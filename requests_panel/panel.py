from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutine

import requests
import requests.sessions
from debug_toolbar.panels import Panel
from debug_toolbar.utils import get_stack_trace, render_stacktrace
from django.utils.http import parse_header_parameters
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

logger = logging.getLogger(__name__)

MASK = '******'
MASKED_REQUEST_HEADERS = frozenset({'authorization', 'proxy-authorization', 'cookie', 'x-api-key'})
MASKED_RESPONSE_HEADERS = frozenset({'set-cookie'})
#: Bodies larger than this are truncated before being stored in the toolbar's store.
MAX_BODY_SIZE = 64 * 1024
TEXT_MEDIA_TYPES = ('text/', 'application/xml', 'application/x-www-form-urlencoded', 'application/javascript')

_REQUESTS_DIR = os.path.dirname(requests.__file__)
_THIS_FILE = __file__

#: Per-request bucket for the recorded HTTP calls. ``None`` means "not collecting".
_collected: ContextVar[list[dict] | None] = ContextVar('djdt_requests_collected', default=None)
#: ``Session.send`` calls itself recursively while following redirects; only the outermost call is recorded.
_send_depth: ContextVar[int] = ContextVar('djdt_requests_send_depth', default=0)


def _mask_headers(headers, masked_names) -> list[list[str]]:
    return [[name, MASK if name.lower() in masked_names else value] for name, value in headers.items()]


def _is_json(media_type: str) -> bool:
    return media_type == 'application/json' or media_type.endswith('+json')


def _is_text(media_type: str) -> bool:
    return _is_json(media_type) or media_type.startswith(TEXT_MEDIA_TYPES)


def _pretty_json(text: str) -> str:
    try:
        return json.dumps(json.loads(text), indent=2, sort_keys=True, ensure_ascii=False)
    except ValueError:
        return text


def _truncate(text: str) -> str:
    if len(text) > MAX_BODY_SIZE:
        return text[:MAX_BODY_SIZE] + '\n… (truncated)'
    return text


def _format_body(data, content_type_header, default_charset='utf-8') -> tuple[str, int | None]:
    """
    Return a display string and the size in bytes (``None`` if unknown) for a request or response body.
    """
    if data is None or data == b'' or data == '':
        return '', 0
    if isinstance(data, str):
        data = data.encode('utf-8', errors='replace')
    if not isinstance(data, (bytes, bytearray)):
        # file objects, generators, ... (streamed uploads)
        return '<streaming body, not captured>', None

    media_type, params = parse_header_parameters(content_type_header or '')
    media_type = media_type.lower()
    size = len(data)
    if media_type and not _is_text(media_type):
        return f'<binary content, {size} bytes>', size

    text = data.decode(params.get('charset') or default_charset, errors='replace')
    if _is_json(media_type):
        text = _pretty_json(text)
    return _truncate(text), size


def _filter_stacktrace(trace):
    """Drop frames inside ``requests`` and this module; the call depth inside ``requests`` varies."""
    return [
        frame for frame in trace if not (frame[0] == _THIS_FILE or frame[0].startswith(_REQUESTS_DIR + os.path.sep))
    ]


def build_record(request, response, send_kwargs) -> dict:
    """Build a JSON-serializable record for a completed ``requests`` call."""
    request_body, request_body_size = _format_body(request.body, request.headers.get('Content-Type'))

    if send_kwargs.get('stream'):
        response_content, response_size = None, None
    else:
        response_content, response_size = _format_body(
            response.content, response.headers.get('Content-Type'), response.encoding or 'utf-8'
        )

    # ``response.history`` holds the intermediate responses; append the final one so the chain is complete.
    chain = [*response.history, response] if response.history else []

    return {
        'method': (request.method or '').upper(),
        'url': request.url,
        'status_code': response.status_code,
        'reason': response.reason or '',
        'elapsed': sum(hop.elapsed.total_seconds() for hop in [*response.history, response]),
        'request_headers': _mask_headers(request.headers, MASKED_REQUEST_HEADERS),
        'request_body': request_body,
        'request_body_size': request_body_size,
        'response_headers': _mask_headers(response.headers, MASKED_RESPONSE_HEADERS),
        'response_content': response_content,
        'response_size': response_size,
        'redirects': [
            {'method': (hop.request.method or '').upper(), 'url': hop.url, 'status_code': hop.status_code}
            for hop in chain
        ],
        'stacktrace': _filter_stacktrace(get_stack_trace(skip=1)),
    }


def _instrument():
    """Wrap ``requests.sessions.Session.send`` so that every HTTP call is recorded. Idempotent."""
    original = requests.sessions.Session.send
    if getattr(original, '_djdt_requests_patched', False):
        return

    @wraps(original)
    def send(self, request, **kwargs):
        depth = _send_depth.get()
        token = _send_depth.set(depth + 1)
        try:
            response = original(self, request, **kwargs)
        finally:
            _send_depth.reset(token)
        if depth == 0:
            bucket = _collected.get()
            if bucket is not None:
                try:
                    bucket.append(build_record(request, response, kwargs))
                except Exception:
                    logger.exception('requests_panel: failed to record HTTP call')
        return response

    send._djdt_requests_patched = True
    requests.sessions.Session.send = send


class RequestsDebugPanel(Panel):
    """
    A Django Debug Toolbar panel that displays HTTP requests made with `requests`.
    """

    title = _('HTTP Requests')
    nav_title = _('HTTP Requests')
    template = 'requests_panel/panel.html'
    has_content = True
    is_async = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._records: list[dict] = []

    @classmethod
    def ready(cls):
        _instrument()

    @property
    def nav_subtitle(self):
        count = len(self.get_stats().get('requests', ()))
        return ngettext('%(count)d request', '%(count)d requests', count) % {'count': count}

    def process_request(self, request):
        token = _collected.set([])
        try:
            response = super().process_request(request)
        except BaseException:
            self._finish(token)
            raise
        if iscoroutine(response):
            return self._aprocess_request(token, response)
        self._finish(token)
        return response

    async def _aprocess_request(self, token, response_coroutine):
        try:
            return await response_coroutine
        finally:
            self._finish(token)

    def _finish(self, token):
        self._records = _collected.get() or []
        try:
            _collected.reset(token)
        except ValueError:
            # The token was created in a different context; stop collecting in this one instead.
            _collected.set(None)

    def generate_stats(self, request, response):
        for record in self._records:
            trace = record.get('stacktrace')
            record['stacktrace'] = str(render_stacktrace(trace)) if trace else ''
        self.record_stats({'requests': self._records})

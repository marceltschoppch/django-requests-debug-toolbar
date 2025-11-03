import contextlib
import json
import threading
from contextvars import ContextVar

from debug_toolbar import settings as dt_settings
from debug_toolbar.panels import Panel
from debug_toolbar.utils import get_stack, render_stacktrace, tidy_stacktrace
from django.utils.functional import cached_property
from django.utils.http import parse_header_parameters
from django.utils.translation import gettext_lazy as _, ngettext
import requests
import requests.sessions


collected_requests = ContextVar('djdt_requests_collected_requests')


def collect(request_info):
    with contextlib.suppress(LookupError):
        collected_requests.get().append(request_info)


class RequestInfo:
    def __init__(self, request, response, kwargs):
        self.request = request
        self.response = response
        self.kwargs = kwargs
        if dt_settings.get_config()['ENABLE_STACKTRACES']:
            self.raw_stacktrace = tidy_stacktrace(reversed(get_stack()[5:]))
        else:
            self.raw_stacktrace = []

    @cached_property
    def stacktrace(self):
        return render_stacktrace(self.raw_stacktrace)

    @cached_property
    def request_headers(self):
        return '\n'.join(
            f'{k}: {"******" if k.lower() == "authorization" else v}' for k, v in self.request.headers.items())

    def _format_json(self, content):
        try:
            return json.dumps(json.loads(content), indent=2, sort_keys=True)
        except Exception:
            # ignore JSON parse exceptions and return unparsed body instead
            import logging
            logging.getLogger(__name__).exception('')
            pass
        return content

    def _is_json(self, content_type):
        if not content_type:
            return False
        media_type, sub = content_type.split('/', 1)
        return media_type == 'application' and sub.split('+').pop() == 'json'

    @cached_property
    def request_body(self):
        if self.request.body:
            content_type = self.request.headers.get('content-type')
            if content_type:
                content_type, params = parse_header_parameters(content_type)
                if self._is_json(content_type):
                    return self._format_json(self.request.body)
                if isinstance(self.request.body, bytes) and params.get('charset'):
                    return self.request.body.decode(params['charset'])
        return self.request.body

    @cached_property
    def response_headers(self):
        return '\n'.join(
            f'{k}: {v}' for k, v in self.response.headers.items())

    @cached_property
    def response_content(self):
        if self.response.content:
            if self.response.headers.get('content-type'):
                content_type, params = parse_header_parameters(self.response.headers['content-type'])
                if self._is_json(content_type):
                    return self._format_json(self.response.content)
            return self.response.text
        return self.response.text


class PatchedSession(requests.sessions.Session):
    """
    A patched requests `Session` class that collects all requests and responses.
    """

    def send(self, request, **kwargs):
        response = super().send(request, **kwargs)
        collect(RequestInfo(request, response, kwargs))
        return response


requests.Session = PatchedSession
requests.sessions.Session = PatchedSession


class RequestsDebugPanel(Panel):
    """
    A Django Debug Toolbar Panel that displays HTTP requests made with `requests`.
    """

    title = _('HTTP Requests')
    nav_title = title
    template = 'requests_panel/panel.html'
    has_content = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_count = 0
        self.collected_requests = []

    @property
    def nav_subtitle(self):
        return ngettext('%(count)s request', '%(count)s requests', self.request_count) % {
            'count': self.request_count,
        }

    def process_request(self, request):
        reset_token = collected_requests.set([])
        response = super().process_request(request)
        self.collected_requests = collected_requests.get().copy()
        collected_requests.reset(reset_token)
        return response

    def generate_stats(self, request, response):
        self.request_count = len(self.collected_requests)
        self.record_stats({
            'requests': self.collected_requests,
        })

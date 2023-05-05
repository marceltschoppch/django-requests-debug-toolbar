import cgi
import json
import threading

from debug_toolbar import settings as dt_settings
from debug_toolbar.panels import Panel
from debug_toolbar.utils import get_stack, render_stacktrace, ThreadCollector, tidy_stacktrace
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _, ngettext
import requests
import requests.sessions


collector = ThreadCollector()


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
            pass
        return content

    @cached_property
    def request_body(self):
        if self.request.body:
            content_type = self.request.headers.get('content-type')
            if content_type:
                content_type, params = cgi.parse_header(content_type)
                if content_type == 'application/json':
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
            if self.response.headers['content-type'] == 'application/json':
                return self._format_json(self.response.content)
            if isinstance(self.response.content, bytes):
                return self.response.content.decode(self.response.encoding)
        return self.response.content


class PatchedSession(requests.sessions.Session):
    """
    A patched requests `Session` class that collects all requests and responses.
    """

    def send(self, request, **kwargs):
        response = super().send(request, **kwargs)
        collector.collect(RequestInfo(request, response, kwargs))
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
        self._local = threading.local()

    @property
    def nav_subtitle(self):
        request_count = getattr(self._local, 'request_count', 0)
        return ngettext('%(count)s request', '%(count)s requests', request_count) % {
            'count': request_count,
        }

    def process_request(self, request):
        collector.clear_collection()
        return super().process_request(request)

    def generate_stats(self, request, response):
        requests = collector.get_collection()
        collector.clear_collection()
        self._local.request_count = len(requests)
        self.record_stats({
            'requests': requests,
        })

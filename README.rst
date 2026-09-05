django-requests-debug-toolbar
=============================

A `Django Debug Toolbar <https://django-debug-toolbar.readthedocs.io/>`_ panel that lists all
HTTP requests made with the popular `requests <https://requests.readthedocs.io/>`_ library
during a Django request.

For every call the panel shows method, URL, status, elapsed time, redirects, request and
response headers, request and response bodies and the Python stack trace of the call.


Requirements
------------

- Python 3.10+
- Django 5.2+
- django-debug-toolbar 6.0+
- requests


Installation
------------

#. Install the package::

    pip install django-requests-debug-toolbar

#. Add ``requests_panel`` to ``INSTALLED_APPS``::

    INSTALLED_APPS = [
        # ...
        'debug_toolbar',
        'requests_panel',
    ]

#. Add the panel to ``DEBUG_TOOLBAR_PANELS``. If you have not customised the panel list yet,
   copy the default list from the django-debug-toolbar documentation and append the panel::

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.history.HistoryPanel',
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.alerts.AlertsPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
        'requests_panel.panel.RequestsDebugPanel',
    ]


What is recorded
----------------

- Method, URL, status code and reason, elapsed time and the redirect chain.
- Request and response headers. ``Authorization``, ``Proxy-Authorization``, ``Cookie``,
  ``X-Api-Key`` and ``Set-Cookie`` values are masked.
- Request and response bodies. JSON bodies (``application/json`` and ``*+json``) are
  pretty-printed, binary bodies are replaced with a placeholder and bodies larger than 64 KiB
  are truncated.
- A stack trace of the call. This follows the django-debug-toolbar settings
  ``ENABLE_STACKTRACES``, ``ENABLE_STACKTRACES_LOCALS`` and ``HIDE_IN_STACKTRACES``.

The panel works with both WSGI and ASGI (async views).


Limitations
-----------

- Only the ``requests`` library is instrumented, not ``httpx`` or ``urllib3`` directly.
- Calls made with ``stream=True`` are listed, but their response body is not captured.
- Calls made in threads that do not propagate context variables (for example a plain
  ``ThreadPoolExecutor``) are not recorded. ``sync_to_async`` propagates them, so calls from
  async views are recorded.


Development
-----------

::

    uv sync
    uvx ruff check .
    uvx ruff format .
    uvx pre-commit install

See ``CHANGELOG.rst`` for release notes.


Contributing
------------

All suggestions are welcome.

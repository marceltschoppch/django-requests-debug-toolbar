Changelog
=========

0.1.0 (2026-09-05)
------------------

Breaking changes
~~~~~~~~~~~~~~~~

- Requires Python 3.10+, Django 5.2+ and django-debug-toolbar 6.0+.
- ``requests`` is now declared as a dependency.
- Packaging moved to ``pyproject.toml`` with hatchling; ``setup.py`` was removed.
- Redirects are shown as a chain below the logical call instead of one entry per hop, and the
  elapsed time is the sum over all hops. Previously the final response of a redirected call
  appeared twice.

Fixed
~~~~~

- Recorded data is now JSON-serializable. With django-debug-toolbar 6.0+, which serializes
  all panel stats, the panel previously showed ``str()`` representations of the request objects.
- Labels in the panel template were rendered empty because ``{{ _("...") }}`` is not valid in
  Django templates. They now use ``{% translate %}``.
- Non-JSON bodies with a JSON content type no longer log a full traceback.
- ``requests.Session`` is no longer replaced with a subclass at import time. Instead
  ``Session.send`` is wrapped when the toolbar starts, so sessions imported earlier and custom
  ``Session`` subclasses are recorded as well.
- Replaced the deprecated ``get_stack``/``tidy_stacktrace`` helpers with ``get_stack_trace``.

Added
~~~~~

- Async/ASGI support.
- ``Proxy-Authorization``, ``Cookie``, ``X-Api-Key`` and ``Set-Cookie`` headers are masked in addition
  to ``Authorization``.
- Response bodies of ``stream=True`` requests are no longer consumed by the panel.
- Bodies are truncated at 64 KiB and binary bodies are replaced with a placeholder.

Removed
~~~~~~~

- Unused ``requests_panel.tracker`` module.

0.0.8 (2025-11-03)
------------------

- Python 3.14 compatibility.

0.0.7 (2024-01-31)
------------------

- Recognize ``+json`` variants in the content-type header.

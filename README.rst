django-requests-debug-toolbar
=============================

A `Django Debug Toolbar <https://django-debug-toolbar.readthedocs.io/>`_ panel for Requests

About
-----

Django Requests Debug Toolbar tracks all HTTP requests made with the popular
`requests <https://requests.readthedocs.io/>`_ library.


Usage
-----

#. Install using pip::

    pip install django-requests-debug-toolbar

#. Add ``requests_panel`` to your ``INSTALLED_APPS`` setting.
#. Add ``requests_panel.panel.RequestsDebugPanel`` to your ``DEBUG_TOOLBAR_PANELS``.


Contributing
------------

All suggestions are welcome.

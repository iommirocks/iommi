try:
    from django.utils.safestring import SafeText
    from django.test import RequestFactory

except ImportError:
    from jinja2 import Markup as SafeText  # noqa

    class RequestFactory:
        def method(self, method, url, params, body=None, root_path=None):
            from flask.ctx import AppContext
            from flask import Flask
            import os
            if not root_path:
                root_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib/tri/form/', )
            app = AppContext(Flask('tri_form', root_path=root_path))
            app.push()
            from werkzeug.test import create_environ
            from tri_form.compat import HttpRequest
            return HttpRequest(create_environ(path=url, query_string=params, method=method, data=body))

        def get(self, url, params=None):
            return self.method('GET', url, params=params)

        def post(self, url, params=None):
            return self.method('POST', url, params={}, body=params)

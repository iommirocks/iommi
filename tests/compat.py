from iommi.base import items

try:
    from django.utils.safestring import SafeText
    from django.test import RequestFactory

except ImportError:
    from jinja2 import Markup as SafeText  # noqa

    class RequestFactory:
        def method(self, method, url, params, body=None, root_path=None, **headers):
            from flask.ctx import AppContext
            from flask import Flask
            import os
            if not root_path:
                root_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'iommi/', )
            app = AppContext(Flask('iommi', root_path=root_path))
            app.push()
            from werkzeug.test import create_environ
            from iommi._web_compat import HttpRequest

            # We use the django style where headers are HTTP_
            for k, v in items(headers):
                assert k.startswith('HTTP_')

            # ...but flask adds HTTP_ itself, so we have to cut them off here
            headers = {k[len('HTTP_'):]: v for k, v in items(headers)}

            return HttpRequest(create_environ(path=url, query_string=params, method=method, data=body, headers=headers))

        def get(self, url, params=None, **headers):
            return self.method('GET', url, params=params, **headers)

        def post(self, url, params=None, **headers):
            return self.method('POST', url, params={}, body=params, **headers)

class HttpRequest:
    def __init__(self, environ):
        from flask import Request

        self.r = Request(environ)

    @property
    def POST(self):  # noqa: N802
        return self.r.form

    @property
    def GET(self):  # noqa: N802
        return self.r.args

    @property
    def method(self):
        return self.r.method

    @property
    def META(self):  # noqa: N802
        return self.r.environ

    def is_ajax(self):
        return self.r.environ.get("HTTP_X_REQUESTED_WITH", "").lower() == "xmlhttprequest"

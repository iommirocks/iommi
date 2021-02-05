class HttpRequest:
    def __init__(self, environ):
        from flask import Request

        self.r = Request(environ)

    @property
    def POST(self):
        return self.r.form

    @property
    def GET(self):
        return self.r.args

    @property
    def method(self):
        return self.r.method

    @property
    def META(self):
        return self.r.environ

    def is_ajax(self):
        return self.r.environ.get("HTTP_X_REQUESTED_WITH", "").lower() == "xmlhttprequest"

import contextvars

_current_request: contextvars.ContextVar = contextvars.ContextVar('_current_request', default=None)


def get_current_request():
    return _current_request.get()


def set_current_request(request):
    _current_request.set(request)

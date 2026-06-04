import contextvars

from django.http import HttpRequest

_current_request: contextvars.ContextVar[HttpRequest | None] = contextvars.ContextVar('_current_request', default=None)


def get_current_request() -> HttpRequest | None:
    return _current_request.get()


def set_current_request(request: HttpRequest | None) -> None:
    _current_request.set(request)

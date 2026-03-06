from django.conf import settings
from django.utils.module_loading import import_string


def test_all_middleware_async_capable():
    not_async = [
        mw_path
        for mw_path in settings.MIDDLEWARE
        if not getattr(import_string(mw_path), 'async_capable', False)
    ]
    assert not not_async, 'Middleware not async capable:\n' + ''.join(f'    {mw}\n' for mw in not_async)

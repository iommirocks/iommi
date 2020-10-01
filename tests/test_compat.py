# This is for testing the compat stuff in tests, not the main iommi compat components
from tests.compat_flask import Jinja2RequestFactory


def test_jinja2_request_factory():
    Jinja2RequestFactory().get('/', params={'foo': 'bar'}, HTTP_HOST='7')


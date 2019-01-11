import pytest


def pytest_runtest_setup(item):
    django_marker = item.get_closest_marker("django_db") or item.get_closest_marker("django")
    if django_marker is not None:
        try:
            import django
        except ImportError:
            pytest.skip("test requires django")

    flask_marker = item.get_closest_marker("flask")
    if flask_marker is not None:
        try:
            import flask
        except ImportError:
            pytest.skip('test requires flask')

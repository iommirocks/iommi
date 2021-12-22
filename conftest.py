from pathlib import Path

import pytest


# pragma: no cover
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


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    items[:] = sorted(items, key=lambda x: x.fspath)


def pytest_sessionstart(session):
    from iommi.docs import generate_api_docs_tests

    generate_api_docs_tests((Path(__file__).parent / 'docs').absolute())

from pathlib import Path

import pytest


def pytest_sessionstart(session):
    from iommi.docs import generate_api_docs_tests, write_rst_from_pytest

    write_rst_from_pytest()
    generate_api_docs_tests((Path(__file__).parent).absolute(), verbose=True)
    write_rst_from_pytest()


@pytest.fixture(autouse=True)
def docs_style(settings):
    settings.IOMMI_DEFAULT_STYLE = 'bootstrap_docs'

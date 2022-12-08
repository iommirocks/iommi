import pytest


@pytest.fixture(autouse=True)
def docs_style(settings):
    settings.IOMMI_DEFAULT_STYLE = 'bootstrap_docs'

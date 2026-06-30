"""
Guards for the marketing homepage (``homepage/index.html``).

The code examples on the homepage are generated from :data:`iommi.homepage.SNIPPETS`
(see that module). These tests make sure:

- every snippet actually runs against the live iommi API (so a snippet can't
  silently rot when the API changes), and
- the committed ``homepage/index.html`` is regenerated from those snippets (so
  the page can't drift from the verified source).
"""

import pytest
from django.urls import path

from docs.models import (
    Album,
    Artist,
)
from iommi import (
    Form,
    Page,
    Table,
)
from iommi.homepage import (
    HOMEPAGE_PATH,
    SNIPPETS,
    generate,
)
from tests.helpers import req

pytestmark = pytest.mark.django_db


def _exec(code, **extra_globals):
    # The snippets are written for display: they import from `.models` and (in
    # the install snippet) contain a shell line. Adapt them so they run against
    # the docs test models, then execute them.
    code = code.replace('from .models import', 'from docs.models import')
    code = '\n'.join(line for line in code.splitlines() if line.strip() != 'pip install iommi')
    namespace = {'path': path, 'Table': Table, 'Form': Form, 'Page': Page, **extra_globals}
    exec(compile(code, '<homepage snippet>', 'exec'), namespace)
    return namespace


def _render(part):
    part.bind(request=req('get')).render_to_response()


def test_hero_snippet_runs():
    namespace = _exec(SNIPPETS['hero'])
    _render(namespace['AlbumPage']())


def test_deep_snippet_runs():
    # The example's filter initial does `Artist.objects.get(name='Dio')`.
    Artist.objects.create(name='Dio')
    namespace = _exec('table = (\n' + SNIPPETS['deep'] + '\n)', Album=Album, Artist=Artist)
    _render(namespace['table'])


def test_filters_snippet_runs():
    namespace = _exec(SNIPPETS['filters'], Album=Album)
    _render(namespace['AlbumTable']())


def test_install_snippet_runs():
    namespace = _exec(SNIPPETS['install'])
    _render(namespace['AlbumPage']())
    # The install snippet also wires up a url; make sure it's a usable urlconf.
    assert len(namespace['urlpatterns']) == 1


def test_homepage_is_up_to_date():
    text = HOMEPAGE_PATH.read_text()
    assert generate(text) == text, 'homepage/index.html is stale - run `make homepage` to regenerate it.'

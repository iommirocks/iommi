import pytest
from bs4 import BeautifulSoup
from django.db import models
from django.test import (
    override_settings,
    RequestFactory,
)

from iommi.page import (
    html,
    Page,
)
from iommi.table import Table
from iommi.base import group_paths_by_children, GroupPathsByChildrenError
from tri_struct import Struct

pytestmark = pytest.mark.django_db

# assert first in children, f'Found invalid path {k}. {first} not a member of {children.keys()}'


class T1(models.Model):
    foo = models.CharField(max_length=255)
    bar = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)


class T2(models.Model):
    foo = models.CharField(max_length=255)
    bar = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)


request = RequestFactory().get('/')  # TODO: we shouldn't need this, but tri.query eagerly tries to read request parameters. We should fix that.


class MyPage(Page):
    t1 = Table.from_model(
        request=request,
        model=T1,
        column__foo=dict(
            query__show=True,
            query__gui__show=True,
        ),
        column__bar=dict(
            query__show=True,
            query__gui__show=True,
        ),
        default_child=True,
    )

    t2 = Table.from_model(
        request=request,
        model=T2,
        column__foo=dict(
            query__show=True,
            query__gui__show=True,
        ),
        column__bar=dict(
            query__show=True,
            query__gui__show=True,
        ),
    )


def test_happy_path():
    my_page = MyPage()

    data = {
        't1/query/gui/foo': '1',
        't2/query/gui/foo': '2',
        'bar': '3',
        't2/bar': '4',
    }

    assert group_paths_by_children(children=my_page.children, data=data) == {
        't1': {
            'query/gui/foo': '1',
            'bar': '3',
        },
        't2': {
            'query/gui/foo': '2',
            'bar': '4',
        },
    }

    assert group_paths_by_children(
        children=my_page.children.t1.children,
        data={
            'query/gui/foo': '1',
            'bar': '3',
        },
    ) == {
        'query': {
            'gui/foo': '1',
            'bar': '3',
        }
    }

    assert group_paths_by_children(
        children=my_page.children.t1.children.query.children,
        data={
            'gui/foo': '1',
            'bar': '3',
        },
    ) == {
        'gui': {
            'foo': '1',
            'bar': '3',
        }
    }


def test_error_message():
    class NoDefaultChildPage(Page):
        foo = html.h1('asd')

    my_page = NoDefaultChildPage()

    data = {
        'unknown': '5',
    }

    with pytest.raises(GroupPathsByChildrenError):
        group_paths_by_children(children=my_page.children, data=data)


def test_error_message_to_client():
    my_page = MyPage()
    my_page.render_or_respond(request=RequestFactory().get('/', data={'/qwe': ''}))
    # TODO: parse response json, check that it contains an error message
    assert False


def test_correct_new_style_dispatch():
    assert False


def test_page_constructor():
    class MyPage(Page):
        h1 = html.h1()

    my_page = MyPage(
        parts=[html.div(name='foo')],
        part__bar=html.div()
    )

    assert len(my_page.parts) == 3
    assert ['foo', 'h1', 'bar'] == list(my_page.parts.keys())


@override_settings(
    MIDDLEWARE_CLASSES=[],
)
def test_page_render():
    class MyPage(Page):
        header = html.h1('Foo')
        body = html.div('bar bar')

    my_page = MyPage()

    request = RequestFactory().get('/')
    request.user = Struct()
    response = my_page.render_to_response(
        request=request,
        template_name='iommi/form/base.html',
    )

    expected_html = '''
        <html>
            <head></head>
            <body>
                 <h1> Foo </h1>
                 <div> bar bar </div>
            </body>
        </html>
    '''

    actual = BeautifulSoup(response.content, 'html.parser').prettify()
    expected = BeautifulSoup(expected_html, 'html.parser').prettify()
    assert actual == expected

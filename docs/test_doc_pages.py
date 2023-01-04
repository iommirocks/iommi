from docs.models import *
from iommi import *
from tests.helpers import (
    req,
    show_output_collapsed,
)

request = req('get')

from iommi.fragment import Fragment
from iommi._web_compat import Template
import pytest
pytestmark = pytest.mark.django_db


def test_pages():
    # language=rst
    """
    Pages
    =====

    iommi pages are used to compose parts of a page into a full page.

    """
    

def test_example():
    # language=rst
    """
    Example
    -------

    """

    # @test
    from django.contrib.auth.models import User
    from iommi import (
        Page,
        html,
        Table,
    )
    # @end

    class MyPage(Page):
        title = html.h1('My page')
        users = Table(auto__model=User)
        create_user = Form.create(auto__model=User)

    # language=rst
    """
    This creates a page with an h1 tag, a table of users and a form to create a
    new user. You can add it your `urls.py` like this: `path('my_page/', MyPage().as_view())`, or make a function based view and `return MyPage()`.
    """

    # @test
    show_output_collapsed(MyPage())
    # @end


def test_page(small_discography):
    # language=rst
    """
    Page
    ----

    The `Page` class is used to compose pages. If you have installed the iommi
    middleware you can also return them directly from your views. They accept
    `str`, `Part` and Django `Template` types:
    """

    # @test
    class MyOtherPage(Page):
        pass
    # @end

    class MyPage(Page):
        # Using the html builder to create a tag safely
        h1 = html.h1('Welcome!')

        # If you write an html tag in here it will be
        # treated as unsafe and escaped by Django like normal
        body_text = 'Welcome to my iommi site...'

        # You can nest Page objects!
        some_other_page = MyOtherPage()

        # Table and Form are Part types
        my_table = Table(auto__model=Artist)

        # Django template
        other_stuff = Template('<div>{{ foo }}</div>')

    # language=rst
    """
    The types here that aren't `Part` will be converted to a `Part` derived class
    as needed.
    """

    # @test
    show_output_collapsed(MyPage(context__foo='foo!'))
    # @end


# language=rst
"""
html
----


html is a little builder object to create simple elements. You just do
`html.h1('some text')` to create an h1 html tag. It works by creating `Fragment`
instances, so the `html.h1('foo')` is the same as
`Fragment('some text', tag='h1')`, which is itself a convenient short way to
write `Fragment(children__text='some text', tag='h1')`. See `Fragment` for more
available parameters.


Part
--------

`Part` is the base class/API for objects that can be composed into a page.


"""


def test_fragment():
    # language=rst
    """
    Fragment
    --------

    Advanced example:


    """
    Fragment(
        'foo',
        tag='div',
        children__bar=Fragment('bar'),
        attrs__baz='quux',
    )

    # language=rst
    """
    This fragment will render as:

    .. code-block:: html

        <div baz='quux'>foobar</div>

    This might seem overly complex for such a simple thing, but when used in
    reusable components in iommi `Fragment` objects can be further customized
    with high precision.
    """

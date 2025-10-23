from iommi import *
from iommi.docs import (
    show_output,
    show_output_collapsed,
)
from tests.helpers import req

request = req('get')

from tests.helpers import req
from django.template import Template
from datetime import date
import pytest
pytestmark = pytest.mark.django_db


def test_parts__pages():
    # language=rst
    """
    Parts & Pages
    -------------

    """


def test_how_do_i_override_part_of_a_part_page():
    # language=rst
    """
    .. _override-part-of-page:

    How do I override part of a part/page?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Page.parts
    .. uses Fragment.children
    .. Attrs

    This is all just *standard* iommi declarative magic, but as you are likely new to it
    this might take a while to get used to. Let's say you created yourself a master template
    for your site.


    """
    class BasePage(Page):
        title = html.h1('My awesome webpage')
        subtitle = html.h2('It rocks')

    # @test
    show_output(BasePage())
    # @end

    # language=rst
    """
    Which you can use like this:

    """
    class IndexPage(BasePage):
        body = 'body'

    index = IndexPage(parts__subtitle__children__child='Still rocking...').as_view()

    # @test
    show_output(index(req('get')))
    # @end

    # language=rst
    """
    or as a function based view:
    """

    def index(request):
        return IndexPage(parts__subtitle__children__child='Still rocking...')

    # @test
    show_output_collapsed(index(req('get')))
    # @end

    # language=rst
    """
    Here you can see that `Part` s (`Page` s are themselves `Part` s) form a tree and the direct children are gathered in the `parts` namespace. Here we overwrote a leaf of
    an existing namespace, but you can also add new elements or replace bigger
    parts (and most of the time it doesn't matter if you use the `class Meta` or the
    keyword arguments to init syntax):
    """

    class IndexPage(BasePage):
        title = html.img(
            attrs=dict(
                src='https://docs.iommi.rocks/_static/logo_with_outline.svg',
                alt='iommi logo',
                width='70px',
            ),
        )

    index = IndexPage(parts__subtitle=None)

    # @test
    show_output(index)
    # @end

    # language=rst
    """
    In the above we replaced the title and removed the subtitle element completely. The
    latter of which shows one of the gotchas as only `str`, `Part` and the django
    template types are gathered into the parts structure when a `Part` class definition
    is processed. As `None` is not an instance of those types, you can remove things
    by setting their value to `None`.

    """


def test_how_do_i_set_the_title_of_my_page():
    # language=rst
    """
    .. _title-of-page:

    How do I set the title of my page?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Page.title

    As in the text shown in the browser status bar?

    """
    Page(title='The title in the browser')

    # language=rst
    """
    Note that this is different from
    """

    class MyPage(Page):
        title = Header('A header element in the dom')

    MyPage()

    # language=rst
    """
    Which is equivalent to:
    """

    Page(parts__title=Header('A header element in the dom'))


def test_how_do_i_specify_the_context_used_when_a_template_is_rendered():
    # language=rst
    """
    .. _context-of-page:

    How do I specify the context used when a Template is rendered?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Page.context


    """
    class MyPage(Page):
        body = Template("""A django template was rendered on {{today}}.""")


    def index(request):
        context = {'today': date.today()}

        return MyPage(context=context)

    # @test
    show_output(index(req('get')))
    # @end

    # language=rst
    """
    You can also insert items in the context via the declaration. This
    not only makes the above shorter, but also makes it easy to write abstractions that
    can be extended later:
    """

    my_page = Page(
        parts__body=Template("""A django template was rendered on {{today}}."""),
        context__today=lambda **_: date.today(),
    ).as_view()

    # @test
    show_output(my_page(req('get')))
    # @end

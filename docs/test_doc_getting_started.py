from django.urls import (
    path,
)

from iommi import *
from iommi.docs import show_output
from tests.helpers import req

request = req('get')

from tests.helpers import req
import pytest
pytestmark = pytest.mark.django_db


def test_getting_started():
    # language=rst
    """
    .. _getting-started:

    Getting started
    ===============

    .. note::

        This guide is intended for a reader that is well versed in the Django basics of the ORM,
        urls routing, function based views, and templates.
    """


# noinspection PyUnusedLocal
def test_1__install():
    # language=rst
    """
    1. Install
    ----------

    First:

    `pip install iommi`.

    Add `iommi` to installed apps:


    """
    INSTALLED_APPS = [
        # [...]
        'iommi',
    ]

    # language=rst
    """
    Add iommi's middleware:


    """
    MIDDLEWARE = [
        # These three are optional, but highly recommended!
        'iommi.live_edit.Middleware',

        # [... Django middleware ...]

        'iommi.sql_trace.Middleware',
        'iommi.profiling.Middleware',

        # [... your other middleware ...]

        'iommi.middleware',
    ]

    # language=rst
    """
    .. note::

        The iommi middleware must be the last middleware in the list!

    By default iommi uses a very basic bootstrap base template. We'll get to how to integrate it into your site later.
    """


def test_2__your_first_form():
    # language=rst
    """
    2. Your first form
    ------------------

    From this point this guide is aimed at users trying iommi in an existing project. :doc:`The tutorial <tutorial>` is a more in-depth guide to building a full application with iommi from scratch.

    Pick a model from your app, and let's build a create form for it! I'm using `Album` here, but you should replace it with your own model. Add this to your `urls.py`:


    """
    from iommi import Form

    # Import any models you need from your models.  Here I'm using Album
    from .models import Album

    urlpatterns = [
        # ...your urls...
        path('iommi-form-test/', Form.create(auto__model=Album).as_view()),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end


def test_3__your_first_table(small_discography):
    # language=rst
    """
    3. Your first table
    -------------------

    Pick a model from your app, and let's build a table for it! Add this to your `urls.py`:


    """
    from iommi import Table

    # Import any models you need from your models.  Here I'm using Album
    from .models import Album

    urlpatterns = [
        # ...your urls...
        path('iommi-table-test/', Table(auto__model=Album).as_view()),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end

    # language=rst
    """
    If you want, add a filter for some column:

    """
    urlpatterns = [
        # ...your urls...
        path('iommi-table-test/', Table(
            auto__model=Album,
            columns__name__filter__include=True,  # <--- replace `name` with some field from your model
        ).as_view()),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end


def test_4__your_first_page():
    # language=rst
    """
    4. Your first page
    ------------------

    Pages are the method to compose complex pages from parts. Add this to your `views.py`:
    """

    from iommi import Page, Form, Table

    # Import any models you need from your models.  Here I'm using Artist
    from .models import Artist

    class TestPage(Page):
        create_form = Form.create(auto__model=Artist)
        a_table = Table(auto__model=Artist)

        class Meta:
            title = 'An iommi page!'

    # language=rst
    """
    then hook into `urls.py`:
    """

    urlpatterns = [
        # ...your urls...
        path(
            'iommi-page-test/',
            TestPage().as_view()
        ),
    ]

    # @test
    show_output(urlpatterns[0])
    # @end


def test_5__a_simple_function_based_view():
    # language=rst
    """
    5. A simple function based view
    -------------------------------

    It's often useful to have a function based view around your iommi code to do
    some basic setup. So we'll add an example for that too. With iommi's
    middleware you can return iommi objects from your view:


    `views.py`:

    """

    # @test
    class TestPage(Page):
        pass
    # @end

    def iommi_view(request, name):
        return TestPage(title=f'Hello {name}')

    # language=rst
    """
    `urls.py`:
    """

    urlpatterns = [
        # ...your urls...
        path(
            'iommi-view-test/<name>/',
            iommi_view
        ),
    ]

    # @test
    show_output(urlpatterns[0].callback(req('get'), name='Tony'))
    # @end


# noinspection PyUnusedLocal
def test_6__make_iommi_pages_fit_into_your_projects_design():
    # language=rst
    """
    6. Make iommi pages fit into your projects design
    -------------------------------------------------

    So far all the views we've created are rendered in plain bootstrap. Let's fit
    the iommi views you've already added into the design of your project.

    The simplest is to add something like this to your `settings.py`:
    """

    # These imports need to be at the bottom of the file!
    from iommi import Style, Asset
    from iommi.style_bootstrap import bootstrap

    IOMMI_DEFAULT_STYLE = Style(
        bootstrap,
        base_template='my_project/iommi_base.html',
        root__assets=dict(
            my_project_custom_css=Asset.css(attrs__href='/static/custom.css'),
            my_project_custom_js=Asset.js(attrs__src='/static/custom.js'),
        ),
    )

    # language=rst
    """
    Where `my_project/iommi_base.html` could look something like this:

    .. code-block:: html

        {% extends "iommi/base.html" %}

        {% block iommi_top %}
            {% include "my_menu.html" %}
        {% endblock %}

        {% block iommi_bottom %}
            {% include "my_footer.html" %}
        {% endblock %}


    After you've set up your base style successfully, all the test pages you made
    before (form, table, page, view) are now using your style.
    """

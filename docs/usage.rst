.. imports
    import pytest
    pytestmark = pytest.mark.django_db
    from iommi import Style


Usage
=====

Install
-------

First `pip install iommi`.

Add `iommi` to installed apps:

.. code:: python

    INSTALLED_APPS = [
        # [...]
        'iommi',
    ]

Add iommi's middleware:

.. code:: python

    MIDDLEWARE = [
        # [...]
        'iommi.middleware',
    ]

By default iommi uses a very basic bootstrap base template. See :doc:`styles <styles>` for
more information how to integrate iommi to your CSS framework.


Basic usage
-----------

You can start by importing `Table` from `iommi` to try it out when
you're just trying it out, but if you want to use iommi long term go read
`production use`_ (it's not long).

When you've done the stuff above you can create a page with a table in it:

.. code:: python

    path('table_as_view/', Table(auto__model=Artist).as_view()),

...or as a function based view:

.. code:: python

    def my_view(request):
        return Table(
            auto__model=Artist,
        )

.. test
    my_view(req('get'))

...or create a table the declarative and explicit way:

.. code:: python

    def my_page(request):
        class MyTable(Table):
            a_column = Column()
            another_column = Column.date()


        return MyTable(rows=Artist.objects.all()).bind(request=request)

.. test
    my_page(req('get'))

Or you can compose a page with two tables:

.. code:: python

    def my_page(request):
        class MyPage(Page):
            artists = Table(auto__model=Artist)
            albums = Table(auto__model=Album)

        return MyPage()

.. test
    my_page(req('get'))



Production use
--------------

You probably want to define your own `Style` in a production scenario. See
:doc:`How to create a Style <styles>`, and especially the section on how to integrate into
an existing code base.

Just like you have your own custom base class for Django's `Model` to have a
central place to put customization you will want to do the same for the base
classes of iommi. In iommi this is even more important since you will almost
certainly want to add more shortcuts that are specific to your product.

Copy this boilerplate to some place in your code and import these classes
instead of the corresponding ones from iommi:

.. code:: python

    import iommi


    class Page(iommi.Page):
        pass


    class Action(iommi.Action):
        pass


    class Field(iommi.Field):
        pass


    class Form(iommi.Form):
        class Meta:
            member_class = Field
            page_class = Page
            action_class = Action


    class Filter(iommi.Filter):
        pass


    class Query(iommi.Query):
        class Meta:
            member_class = Filter
            form_class = Form


    class Column(iommi.Column):
        pass


    class Table(iommi.Table):
        class Meta:
            member_class = Column
            form_class = Form
            query_class = Query
            page_class = Page
            action_class = Action


    class Menu(iommi.Menu):
        pass


    class MenuItem(iommi.MenuItem):
        pass


Under the hood
--------------

You can also use the parts of iommi by themselves, without using the
middleware. With middleware it looks like this:


.. code:: python

    def my_page(request):
        class MyPage(Page):
            title = html.h1('Hello')
            div = html.div('Some text')

        return MyPage()

.. test
    my_page(req('get'))

And without the middleware it looks like:

.. code:: python

    def my_page(request):
        class MyPage(Page):
            title = html.h1('Hello')
            div = html.div('Some text')

        return MyPage().bind(request=request).render_to_response()

.. test
    my_page(req('get'))


You can also do the same thing like this and avoid the view:

.. code:: python

    class MyPage(Page):
        title = html.h1('Hello')
        div = html.div('Some text')

    # urls.py:
    path(r'foo/', MyPage().as_view()),

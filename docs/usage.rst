Usage
=====

Add this to settings.py:

.. code:: python

    # NOTE: if your base template is called "base.html"
    # then you don't need this!
    IOMMI_BASE_TEMPLATE = 'my_base.html'
    # NOTE: if your base template has a content block
    # called "content" then you don't need this!
    IOMMI_CONTENT_BLOCK = 'content'

The base template is the one containing your `<html>` tag and has `{% block content %}`.


Add `iommi` to installed apps:

.. code:: python

    INSTALLED_APPS = [
        ...
        'iommi',
    ]

Add iommi's middleware:

.. code:: python

    MIDDLEWARE = [
        ...
        'iommi.middleware',
    ]


You can start by importing `Table` from `iommi` to try it out when
you're just trying it out, but if you want to use iommi long term go read
`production use`_ (it's not long).

When you've done the stuff above you can create a page with a table in it:

.. code:: python

    url(r'^table_as_view/$', Table.as_view(auto__model=MyModel)),

...or as a function based view:

.. code:: python

    def my_view(request):
        return Table.as_page(
            request=request,
            table__model=MyModel,
        )


...or create a table the declarative and explicit way:

.. code:: python

    class MyTable(Table):
        a_column = Column()
        another_column = Column.date()


    my_table = MyTable(request=request, data=MyModel.objects.all())

and then you can render it in your template:


.. code:: html

    {{ my_table }}


Or you can compose a page with two tables:

.. code:: python

    def my_page(request):
        class MyPage(Page):
            foos = Table(auto__model=Foo)
            bars = Table(auto__model=Bar)

        return MyPage()


Production use
--------------

Just like you have your own custom base class for django `Model` to have a
central place to put customization you will want to do the same for the base
classes of iommi. In iommi this is even more important since you will almost
certain want to add more shortcuts that are specific to your product.

Copy this boilerplate to some place in your code and import these classes
instead of the corresponding ones from iommi:

.. code:: python

    import iommi


    class Action(iommi.Action):
        pass


    class Field(iommi.Field):
        pass


    class Form(iommi.Form):
        class Meta:
            member_class = Field


    class Variable(iommi.Variable):
        pass


    class Query(iommi.Query):
        class Meta:
            member_class = Variable
            form_class = Form


    class Column(iommi.Column):
        pass


    class Table(iommi.Table):
        class Meta:
            member_class = Column
            form_class = Form
            query_class = Query


    class Page(iommi.Page):
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

And without the middleware it looks like:

.. code:: python

    def my_page(request):
        class MyPage(Page):
            title = html.h1('Hello')
            div = html.div('Some text')

        return render_or_respond(request=request, MyPage())

or even more low level:

.. code:: python

    def my_page(request):
        class MyPage(Page):
            title = html.h1('Hello')
            div = html.div('Some text')

        page = MyPage()
        page.bind(request=request)
        dispatch = do_dispatch(page)
        if dispatch:
            return dispatch
        return page.render_to_response()

Usage
=====

Add this to settings.py:

.. code:: python

    # NOTE: if your base template is called "base.html" then you don't need this!
    IOMMI_BASE_TEMPLATE = 'my_base.html'

The base template is the one containing your `<html>` tag and has `{% block content %}`.


Add `iommi` to installed apps:

.. code:: python

    INSTALLED_APPS = [
        ...
        'iommi',
    ]

Add iommi's page middleware:

.. code:: python

    MIDDLEWARE = [
        ...
        'iommi.page_middleware',
    ]


You can start by importing `Table` from `iommi` to try it out when
you're just trying it out, but if you want to use iommi
long term you should put this boilerplate in some module and use these classes.
This is so you have a central place to override or add functionality.


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


When you've done the stuff above you can create a page with a table in it:

.. code:: python

    def my_view(request):
        return Table.as_page(
            request=request,
            table__model=MyModel,
        )


Or create a table the declarative and explicit way:

.. code:: python

    class MyTable(Table):
        a_column = Column()
        another_column = Column.date()


    my_table = MyTable(request=request, data=MyModel.objects.all())

and then you can render it in your template:


TODO: this part doesn't currently work!! Rendering needs to be done my_table.something I think

.. code:: html

    {{ my_table }}


Or you can compose a page with two tables:

.. code:: python

    def my_page(request):
        class MyPage(Page):
            foos = Table.from_model(model=Foo)
            bars = Table.from_model(model=Bar)

        return MyPage()

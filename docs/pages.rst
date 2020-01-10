Pages
=====

iommi pages is used to compose parts of a page into a full page.

.. contents::

Example
-------

.. code:: python

    from django.contrib.auth.models import User
    from iommi import (
        Page,
        html,
        Table,
    )

    def my_view(request):
        class MyPage(Page):
            title = html.h1('My page')
            users = Table.from_model(User)
            create_user = Form.as_create_page(model=User)

        return MyPage()


This creates a page with a h1 tag, a table of users and a form to create a new user.

Page
----

The :code:`Page` class is used to compose pages. If you have installed the iommi middleware you can also return them directly from your views. They accept :code:`str`, :code:`PagePart` and Django :code:`Template` types:

.. code:: python

    class MyPage(Page):
        # Using the html builder to create a tag safely
        h1 = html.h1('Welcome!)

        # If you write an html tag in here it will be
        # treated as unsafe and escaped by Django like normal
        body_text = 'Welcome to my iommi site...'

        # You can nest Page objects!
        some_other_page = MyOtherPage()

        # Table and Form are PagePart types
        my_table = Table.from_model(Foo)

        # Django template
        other_stuff = Template('<div>{{ foo }}</div>')

The types here that aren't :code:`PagePart` will be converted to a :code:`PagePart` derived class as needed.

html
----


html is a little builder object to create simple elements. You just do :code:`html.h1('some text')` to create a h1 html tag. It works by creating :code:`Fragment` instances, so the :code:`html.h1('foo')` is the same as :code:`Fragment('some text', tag='h1')`. See :code:`Fragment` for more available parameters.


PagePart
--------

:code:`PagePart` it the base class/API for objects that can be composed into a page.


Fragment
--------

Advanced example:

.. code:: python

    Fragment(
        'foo',
        tag='div',
        children=[
            Fragment('bar'),
        ],
        attrs__baz='quux',
    )

This fragment will render as:

.. code:: html

    <div baz='quux'>foobar</div>

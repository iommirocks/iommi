Pages
=====

iommi pages is used to compose parts of a page into a full page.

.. contents::
    :local:

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
            users = Table(auto__model=User)
            create_user = Form.create(auto__model=User)

        return MyPage()


This creates a page with an h1 tag, a table of users and a form to create a
new user.

Page
----

The `Page` class is used to compose pages. If you have installed the iommi
middleware you can also return them directly from your views. They accept
`str`, `Part` and Django `Template` types:

.. code:: python

    class MyPage(Page):
        # Using the html builder to create a tag safely
        h1 = html.h1('Welcome!)

        # If you write an html tag in here it will be
        # treated as unsafe and escaped by Django like normal
        body_text = 'Welcome to my iommi site...'

        # You can nest Page objects!
        some_other_page = MyOtherPage()

        # Table and Form are Part types
        my_table = Table(auto__model=Foo)

        # Django template
        other_stuff = Template('<div>{{ foo }}</div>')

The types here that aren't `Part` will be converted to a `Part` derived class
as needed.

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

`Part` it the base class/API for objects that can be composed into a page.


Fragment
--------

Advanced example:

.. code:: python

    Fragment(
        'foo',
        tag='div',
        children__bar=Fragment('bar'),
        attrs__baz='quux',
    )

This fragment will render as:

.. code:: html

    <div baz='quux'>foobar</div>

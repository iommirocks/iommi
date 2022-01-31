
Pages
=====

iommi pages are used to compose parts of a page into a full page.

    


Example
-------


.. code-block:: python

    class MyPage(Page):
        title = html.h1('My page')
        users = Table(auto__model=User)
        create_user = Form.create(auto__model=User)


This creates a page with an h1 tag, a table of users and a form to create a
new user. You can add it your `urls.py` like this: `path('my_page/', MyPage().as_view())`, or make a function based view and `return MyPage()`.

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('1b59f9c8-0a60-4276-afdd-332c2e62e8eb', this)">► Show result</div>
        <iframe id="1b59f9c8-0a60-4276-afdd-332c2e62e8eb" src="doc_includes/pages/test_example.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


Page
----

The `Page` class is used to compose pages. If you have installed the iommi
middleware you can also return them directly from your views. They accept
`str`, `Part` and Django `Template` types:


.. code-block:: python

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


The types here that aren't `Part` will be converted to a `Part` derived class
as needed.

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('1028b4fb-0d0e-452f-b16a-0f912e5d74b4', this)">► Show result</div>
        <iframe id="1028b4fb-0d0e-452f-b16a-0f912e5d74b4" src="doc_includes/pages/test_page.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


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


.. code-block:: python

    Fragment(
        'foo',
        tag='div',
        children__bar=Fragment('bar'),
        attrs__baz='quux',
    )


This fragment will render as:

.. code-block:: html

    <div baz='quux'>foobar</div>

This might seem overly complex for such a simple thing, but when used in
reusable components in iommi `Fragment` objects can be further customized
with high precision.

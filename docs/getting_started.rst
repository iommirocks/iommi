
Getting started
===============

    


1. Install
----------

First:

`pip install iommi`.

Add `iommi` to installed apps:


.. code-block:: python

    INSTALLED_APPS = [
        # [...]
        'iommi',
    ]


Add iommi's middleware:


.. code-block:: python

    MIDDLEWARE = [
        # These three are optional, but highly recommended!
        'iommi.live_edit.Middleware',

        # [... Django middleware ...]

        'iommi.sql_trace.Middleware',
        'iommi.profiling.Middleware',

        # [... your other middleware ...]

        'iommi.middleware',
    ]


.. note::

    The iommi middleware must be the last middleware in the list!

By default iommi uses a very basic bootstrap base template. We'll get to how to integrate it into your site later.


    


2. Your first form
------------------

Pick a model from your app, and let's build a create form for it! I'm using `Album` here, but you should replace it with some your model. Add this to your `urls.py`:


.. code-block:: python

    from iommi import Form

    urlpatterns = [
        # ...your urls...
        path('iommi-form-test/', Form.create(auto__model=Album).as_view()),
    ]

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('194b0829-9c1b-475c-97e2-47ff5dd42bff', this)">▼ Hide result</div>
        <iframe id="194b0829-9c1b-475c-97e2-47ff5dd42bff" src="doc_includes/getting_started/test_2__your_first_form.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


3. Your first table
-------------------

Pick a model from your app, and let's build a table for it! Add this to your `urls.py`:


.. code-block:: python

    from iommi import Table

    urlpatterns = [
        # ...your urls...
        path('iommi-table-test/', Table(auto__model=Album).as_view()),
    ]

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('6e926673-ebb8-4897-a200-8a930aaa00cb', this)">▼ Hide result</div>
        <iframe id="6e926673-ebb8-4897-a200-8a930aaa00cb" src="doc_includes/getting_started/test_3__your_first_table.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

If you want, add a filter for some column:

.. code-block:: python

    urlpatterns = [
        # ...your urls...
        path('iommi-table-test/', Table(
            auto__model=Album,
            columns__name__filter__include=True,  # <--- replace `name` with some field from your model
        ).as_view()),
    ]

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('4c5ef5bd-5c70-4fba-b6f1-4c0d2b0c7b43', this)">▼ Hide result</div>
        <iframe id="4c5ef5bd-5c70-4fba-b6f1-4c0d2b0c7b43" src="doc_includes/getting_started/test_3__your_first_table1.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


4. Your first page
------------------

Pages are the method to compose complex pages from parts. Add this to your `views.py`:


.. code-block:: python

    from iommi import Page, Form, Table

    class TestPage(Page):
        create_form = Form.create(auto__model=Artist)
        a_table = Table(auto__model=Artist)

        class Meta:
            title = 'An iommi page!'


then hook into `urls.py`:


.. code-block:: python

    urlpatterns = [
        # ...your urls...
        path(
            'iommi-page-test/',
            TestPage().as_view()
        ),
    ]

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('02217ffd-b36b-4954-9957-44ed8dbf7e8a', this)">▼ Hide result</div>
        <iframe id="02217ffd-b36b-4954-9957-44ed8dbf7e8a" src="doc_includes/getting_started/test_4__your_first_page.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


5. A simple function based view
-------------------------------

It's often useful to have a function based view around your iommi code to do
some basic setup. So we'll add an example for that too. With iommis
middleware you can return iommi objects from your view:


`views.py`:


.. code-block:: python

    def iommi_view(request, name):
        return TestPage(title=f'Hello {name}')


`urls.py`:


.. code-block:: python

    urlpatterns = [
        # ...your urls...
        path(
            'iommi-view-test/{name}',
            iommi_view
        ),
    ]

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('2835af44-0d9e-41de-949c-48336d88ec5a', this)">▼ Hide result</div>
        <iframe id="2835af44-0d9e-41de-949c-48336d88ec5a" src="doc_includes/getting_started/test_5__a_simple_function_based_view.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


6. Make iommi pages fit into your projects design
-------------------------------------------------

So far all the views we've created are rendered in plain bootstrap. Let's fit
the iommi views you've already added into the design of your project.

The simplest is to add something like this to your `settings.py`:


.. code-block:: python

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

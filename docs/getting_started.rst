.. imports
    from tests.helpers import req, user_req, staff_req
    from django.template import Template
    from tri_declarative import Namespace
    from iommi.attrs import render_attrs
    from django.http import HttpResponseRedirect
    from datetime import date
    import pytest
    pytestmark = pytest.mark.django_db



Getting started
===============

1. Install
----------

First:

`pip install iommi`.

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

.. note::

    The iommi middleware must be the last middleware in the list!

By default iommi uses a very basic bootstrap base template. We'll get to how to integrate it into your site later.


2. Your first form
------------------

Pick a model from your app, and let's build a create form for it! I'm using `Album` here, but you should replace it with some your model. Add this to your `urls.py`:

.. code:: python

    from iommi import Form

    urlpatterns = [
        # ...your urls...
        path('iommi-form-test/', Form.create(auto__model=Album).as_view()),
    ]


3. Your first table
-------------------

Pick a model from your app, and let's build a create form for it! Add this to your `urls.py`:

.. code:: python

    from iommi import Table

    urlpatterns = [
        # ...your urls...
        path('iommi-table-test/', Table(auto__model=Album).as_view()),
    ]


If you want, add a filter for some column:

.. code:: python

    urlpatterns = [
        # ...your urls...
        path('iommi-table-test/', Table(
            auto__model=Album,
            columns__name__filter__include=True,  # <--- replace `name` with some field from your model
        ).as_view()),
    ]


4. Your first page
------------------

Pages are the method to compose complex pages from parts. Add this to your `views.py`:

.. code:: python

    from iommi import Page, Form, Table

    class TestPage(Page):
        create_form = Form.create(auto__model=Artist)
        a_table = Table(auto__model=Artist)

        class Meta:
            title = 'An iommi page!'

then hook into `urls.py`:

.. code:: python

    urlpatterns = [
        # ...your urls...
        path(
            'iommi-page-test/',
            TestPage().as_view()
        ),
    ]


5. Make iommi pages fit into your projects design
-------------------------------------------------

So far all the views we've created are rendered in plain bootstrap. Let's fit
the iommi views you've already added into the design of your project.

The simplest is to add something like this to your `settings.py`:

.. code:: python

    from iommi.style_bootstrap import bootstrap

    IOMMI_DEFAULT_STYLE = Style(
        bootstrap,
        base_template='my_project/iommi_base.html',
        root__assets=dict(
            my_project_custom_css=Asset.css(attrs__href='/static/custom.css'),
            my_project__custom_js=Asset.js(attrs__src='/static/custom.js'),
        ),
    )

Where `my_project/iommi_base.html` could look something like this:

.. code:: html

    {% extends "iommi/base.html" %}

    {% block iommi_top %}
        {% include "my_menu.html" %}
    {% endblock %}

    {% block iommi_bottom %}
        {% include "my_footer.html" %}
    {% endblock %}

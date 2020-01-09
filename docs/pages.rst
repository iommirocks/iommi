Pages
=====

Iommi pages is used to compose parts of a page into a full page.

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


Page
----


html
----


PagePart
--------

`PagePart` it the base class/API for objects that can be composed into a page. `Page` automatically


Fragment
--------

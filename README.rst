.. image:: https://travis-ci.org/TriOptima/tri.form.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.form

.. image:: http://codecov.io/github/TriOptima/tri.form/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/tri.form?branch=master

tri.form
==========

tri.form is a library for creating HTML forms. It is inspired by, and comes from a frustration with, Django forms.

Major features compared to Django forms:

- Supports :code:`__` syntax for going across table boundaries, similar to how Django does with QuerySets.
- Send in a callable that is late evaluated to determine if a field should be displayed (:code:`show`). This is very handy for showing a slightly different form to administrators for example.
- Both declarative interface and traditional API for defining forms (courtesy of tri.declarative). This makes it easy to generate forms programmatically.
- Easy configuration without writing entire classes that are only used in one place anyway.

Example
-------

Declarative style, :code:`show`, configure rendering a bit:

.. code:: python

    class UserForm(Form):
        name = Field()
        username = Field()
        is_admin = Field.boolean(
            show=lambda form, field: form.request.user.is_staff,
            label_template='tweak_label_tag.html',
        )

    def edit_user_view(request):
        form = UserForm(request=request)

You can generate forms from models and still configure small things:

.. code:: python

    form = Form.from_model(request.POST, User, is_admin__label_template='tweak_label_tag.html')

Create forms programmatically:

.. code:: python

    form = Form(fields=[Field(name='username'), Field(name='is_admin')])

Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

http://triform.readthedocs.org.

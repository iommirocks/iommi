Usage
=====

Django
~~~~~~

Add `tri.form` to installed apps or copy the templates to your own
template directory. The templates are compatible with the Django
template engine and Jinja2.


General
~~~~~~~

We recommend you subclass `Form` and `Field` in your own app to
make it easy to override behavior centrally as well as add your own
shortcuts you want to use in your app. A standard boilerplate looks
like this:

.. code-block:: python

    import tri.form


    class Form(tri.form.Form):
        pass


    class Field(tri.form.Field):
        pass

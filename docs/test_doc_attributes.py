# language=rst
"""
.. _attributes:

`attrs`
-------

The `attrs` namespace is used to customize the rendering of HTML attributes.

For example, in this form we add a custom attribute, a CSS class and an inline style specification:

.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__artist__attrs__foo='bar',
        fields__name__attrs__class__bar=True,
        fields__name__attrs__style__baz='qwe',
    )

    # @test
    form.bind(request=req('get')).__html__()
    # @end

or more succinctly:

.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__artist__attrs__foo='bar',
        fields__name__attrs=dict(
            class__bar=True,
            style__baz='qwe',
        )
    )

    # @test
    form.bind(request=req('get')).__html__()
    # @end

The thing to remember is that the basic namespace is a dict with key value
pairs that gets projected out into the HTML, but there are two special cases
for `style` and `class`. The example above will result in the following
attributes on the field tag:

.. code-block:: html

   <div foo="bar" class="bar" style="baz: qwe">

The values in these dicts can be callables:

.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__name__attrs__class__bar=
            lambda request, **_: request.user.is_staff,
    )

Note that the class names are sorted alphabetically on render.


If you need to add a style with `-` in the name you have to do this:


.. code-block:: pycon

    >>> render_attrs(Namespace(**{'style__font-family': 'sans-serif'}))
    ' style="font-family: sans-serif"'

"""

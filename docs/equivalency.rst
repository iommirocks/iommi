
Equivalence
===========

In iommi there are multiple ways to accomplish the same thing. The two most obvious ways are declarative and programmatic. But there are different paths even within those two main paths. This page is an overview of a few of those ways. Hopefully you will see the philosophy through these examples. Let's get started!


First a model:

.. literalinclude:: models.py
     :start-after: # album_start
     :end-before: # album_end
     :language: python


We want to create a form to create an album. We already have the artist from the URL, so that field shouldn't be in the form.

The following forms all accomplish this goal (you can use `form.as_view()` to create a view from a `Form` instance):


.. code-block:: python

    form = Form.create(
        auto__model=Album,
        auto__exclude=['artist'],
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('4400f7fa-4150-445a-9e69-5a0a6d2507fd', this)">▼ Hide result</div>
        <iframe id="4400f7fa-4150-445a-9e69-5a0a6d2507fd" src="doc_includes/equivalency/test_equivalence.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form.create(
        auto=dict(
            model=Album,
            exclude=['artist'],
        ),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('f7e0f46a-6c61-464c-8fa6-9e4304e418db', this)">► Show result</div>
        <iframe id="f7e0f46a-6c61-464c-8fa6-9e4304e418db" src="doc_includes/equivalency/test_equivalence1.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form.create(
        auto__model=Album,
        fields__artist__include=False,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('bfb4038d-bae6-4dc9-9cfa-0944611875ea', this)">► Show result</div>
        <iframe id="bfb4038d-bae6-4dc9-9cfa-0944611875ea" src="doc_includes/equivalency/test_equivalence2.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__exclude = ['artist']

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('83f19eb5-0d71-4987-93d3-b4edaae4d090', this)">► Show result</div>
        <iframe id="83f19eb5-0d71-4987-93d3-b4edaae4d090" src="doc_includes/equivalency/test_equivalence3.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'year']

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('d97bcae6-4985-41e3-ba6e-27713b158f66', this)">► Show result</div>
        <iframe id="d97bcae6-4985-41e3-ba6e-27713b158f66" src="doc_includes/equivalency/test_equivalence4.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            fields__artist__include = False

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('74170b1d-bc61-47b3-93ea-206ad29f0aa4', this)">► Show result</div>
        <iframe id="74170b1d-bc61-47b3-93ea-206ad29f0aa4" src="doc_includes/equivalency/test_equivalence5.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

Without using the `auto` features:


.. code-block:: python

    class ArtistForm(Form):
        name = Field()
        year = Field.integer()

        class Meta:
            title = 'Create album'
            actions__submit__post_handler = create_artist

    form = ArtistForm()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('83a93a78-eaeb-4811-b9f6-64fba9b9a037', this)">► Show result</div>
        <iframe id="83a93a78-eaeb-4811-b9f6-64fba9b9a037" src="doc_includes/equivalency/test_equivalence6.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form(
        fields__name=Field(),
        fields__year=Field.integer(),
        title='Create album',
        actions__submit__post_handler=create_artist,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('8e99054a-d97e-423f-a6c4-454383404848', this)">► Show result</div>
        <iframe id="8e99054a-d97e-423f-a6c4-454383404848" src="doc_includes/equivalency/test_equivalence7.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

You can read more about this in the philosophy section under :ref:`philosophy_hybrid_api`.

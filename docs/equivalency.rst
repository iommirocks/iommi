
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

    
        <div class="iframe_collapse" onclick="toggle('7108f13e-d97b-403f-aef1-760e23cac617', this)">▼ Hide result</div>
        <iframe id="7108f13e-d97b-403f-aef1-760e23cac617" src="doc_includes/equivalency/test_equivalence.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form.create(
        auto=dict(
            model=Album,
            exclude=['artist'],
        ),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('1d2b1ae9-7187-438c-9c5a-a68df640e482', this)">► Show result</div>
        <iframe id="1d2b1ae9-7187-438c-9c5a-a68df640e482" src="doc_includes/equivalency/test_equivalence1.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form.create(
        auto__model=Album,
        fields__artist__include=False,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('7dc4ebbf-fd79-4214-86c9-ac99ad07098b', this)">► Show result</div>
        <iframe id="7dc4ebbf-fd79-4214-86c9-ac99ad07098b" src="doc_includes/equivalency/test_equivalence2.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__exclude = ['artist']

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('e08a16f2-9e80-4ad6-9f63-7b65ef418b61', this)">► Show result</div>
        <iframe id="e08a16f2-9e80-4ad6-9f63-7b65ef418b61" src="doc_includes/equivalency/test_equivalence3.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'year']

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('167c9b9b-c089-408a-9f9a-78d09e1f00c9', this)">► Show result</div>
        <iframe id="167c9b9b-c089-408a-9f9a-78d09e1f00c9" src="doc_includes/equivalency/test_equivalence4.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            fields__artist__include = False

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('b292cf64-51c8-4a97-86e1-b4f3ba15b97b', this)">► Show result</div>
        <iframe id="b292cf64-51c8-4a97-86e1-b4f3ba15b97b" src="doc_includes/equivalency/test_equivalence5.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

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

    
        <div class="iframe_collapse" onclick="toggle('2acbab51-79e0-4647-a9c9-f0d48dbc6656', this)">► Show result</div>
        <iframe id="2acbab51-79e0-4647-a9c9-f0d48dbc6656" src="doc_includes/equivalency/test_equivalence6.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form(
        fields__name=Field(),
        fields__year=Field.integer(),
        title='Create album',
        actions__submit__post_handler=create_artist,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('27def915-94ab-4c82-9c8f-b5e86c886b29', this)">► Show result</div>
        <iframe id="27def915-94ab-4c82-9c8f-b5e86c886b29" src="doc_includes/equivalency/test_equivalence7.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

You can read more about this in the philosophy section under :ref:`philosophy_hybrid_api`.


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

    
        <div class="iframe_collapse" onclick="toggle('47e6d733-5a1f-4505-9742-d14d6fe48fa0', this)">▼ Hide result</div>
        <iframe id="47e6d733-5a1f-4505-9742-d14d6fe48fa0" src="doc_includes/equivalency/test_equivalence.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form.create(
        auto=dict(
            model=Album,
            exclude=['artist'],
        ),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('f5486d25-9097-46d3-839d-e60f059f817f', this)">► Show result</div>
        <iframe id="f5486d25-9097-46d3-839d-e60f059f817f" src="doc_includes/equivalency/test_equivalence1.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form.create(
        auto__model=Album,
        fields__artist__include=False,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('4153e20c-5494-4c8d-a395-a51d5da48d67', this)">► Show result</div>
        <iframe id="4153e20c-5494-4c8d-a395-a51d5da48d67" src="doc_includes/equivalency/test_equivalence2.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__exclude = ['artist']

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('d4b8ac30-5a23-4598-9866-d8da20787e3a', this)">► Show result</div>
        <iframe id="d4b8ac30-5a23-4598-9866-d8da20787e3a" src="doc_includes/equivalency/test_equivalence3.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'year']

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('a91dfce4-44e0-4c5b-b0df-d9cb05b489bb', this)">► Show result</div>
        <iframe id="a91dfce4-44e0-4c5b-b0df-d9cb05b489bb" src="doc_includes/equivalency/test_equivalence4.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            fields__artist__include = False

    form = ArtistForm.create()

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('460f5735-bd64-4e71-b392-67820f9e3e98', this)">► Show result</div>
        <iframe id="460f5735-bd64-4e71-b392-67820f9e3e98" src="doc_includes/equivalency/test_equivalence5.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

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

    
        <div class="iframe_collapse" onclick="toggle('bc2b686e-727c-4d2e-9bae-4e706638c67d', this)">► Show result</div>
        <iframe id="bc2b686e-727c-4d2e-9bae-4e706638c67d" src="doc_includes/equivalency/test_equivalence6.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. code-block:: python

    form = Form(
        fields__name=Field(),
        fields__year=Field.integer(),
        title='Create album',
        actions__submit__post_handler=create_artist,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('f163205b-8e39-4a37-abed-66c218aac259', this)">► Show result</div>
        <iframe id="f163205b-8e39-4a37-abed-66c218aac259" src="doc_includes/equivalency/test_equivalence7.html" style="background: white; display: none; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

You can read more about this in the philosophy section under :ref:`philosophy_hybrid_api`.

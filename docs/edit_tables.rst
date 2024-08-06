

Edit tables
===========

iommi edit tables builds on top of iommi tables but enable editing of cells too.

A simple example:

.. code-block:: python

    EditTable(
        auto__model=Album,
        page_size=10,
        columns__year__field__include=True,
    )

.. raw:: html

    <div class="iframe_collapse" onclick="toggle('c9809678-da61-40d3-a804-59133208aa86', this)">▼ Hide result</div>
    <iframe id="c9809678-da61-40d3-a804-59133208aa86" src="doc_includes/edit_tables/test_edit_tables.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>


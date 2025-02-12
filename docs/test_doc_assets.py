# language=rst
"""
.. _assets:


`assets`
--------

Assets are meant to be the elements that you refer
to in the `<head>` tag of your document such as links to scripts, style sheets, and
inline scripts or css.

Every :doc:`Part` can include the assets it needs. Similarly :doc:`Style` can include assets.
When a part is rendered all assets are automatically collected and included in the `<head>` of the document.

Because assets have names (:doc:`Everything has a name <philosophy>`), assets with the same name will overwrite
each other, resulting in only one asset with a given name being rendered.

You can remove an asset by passing `None` as the value.
"""

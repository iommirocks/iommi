# language=rst
"""
.. _tag:

`tag`
-----

The `tag` config is used to specify what HTML tag the component renders as. For example, you can take a `Table` and give it `tag='div'` to make it render not as `<table>` but as `<div>`. Of course, in that case you need to do the same for the row rendering.

This feature can be used to change the tag used for the :ref:`title` of a component. By default iommi uses :doc:`Header`, which is a special class that automatically infers if it should be `<h1>`, `<h2>`, `<h3>`, etc based on the nesting level. You can then override the `tag` to specify the exact HTML tag you want.

"""

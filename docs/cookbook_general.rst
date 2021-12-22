
General
-------


    


How do I find the path to a parameter?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Navigating the namespaces can sometimes feel a bit daunting. To help with
this iommi has a special debug mode that can help a lot. By default it's
set to settings.DEBUG, but to set it explicitly put this in your settings:


.. code-block:: python

    IOMMI_DEBUG = True


Now iommi will output `data-iommi-path` attributes in the HTML that will
help you find the path to stuff to configure. E.g. in the kitchen
sink table example a cell looks like this:

.. code-block:: html

    <td data-iommi-path="columns__e__cell">explicit value</td>

To customize this cell you can pass for example
`columns__e__cell__format=lambda value, **_: value.upper()`. See below for
many more examples.

Another nice way to find what is available is to append `?/debug_tree` in the
url of your view. You will get a table of available paths with the ajax
endpoint path, and their types with links to the appropriate documentation.

If `IOMMI_DEBUG` is on you will also get two links on the top of your pages
called `Code` and `Tree`. Code will jump to the code for the current view
in PyCharm. You can configure the URL builder to make it open your favored
editor by setting `IOMMI_DEBUG_URL_BUILDER` in settings:


.. code-block:: python

    IOMMI_DEBUG_URL_BUILDER = lambda filename, lineno: f'my_editor://{filename}:{lineno}'


Visual Studio Code example:


.. code-block:: python

    IOMMI_DEBUG_URL_BUILDER=lambda filename, lineno: f"vscode://file/{filename}:{lineno}:0"


The `Tree` link will open the `?/debug_tree` page mentioned above.


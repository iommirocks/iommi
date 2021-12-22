
Style
=====

iommi has the goal to be easy to integrate into your existing code base,
in addition to be being great for developing new products. In order to
accomplish both these goals we need to be able to plug in to whatever
CSS framework you have. By default iommi uses a bootstrap style, but
it also ships with a few other style definitions, and you can define your
own. Styles in iommi do more than just apply CSS classes, you can target
any configuration in iommi with style definitions. This means not just
how things look, but also how they work.

The styles iommi ships with are:




    bootstrap
    bulma
    foundation
    semantic_ui
    water
    django_admin


There are also some internal styles, most notably `base` which is used for
common style data for all styles, and `test` which is used for the tests.

You can change which style your app uses by default by setting
`IOMMI_DEFAULT_STYLE` to the name of your style in the Django settings.




Creating a custom style
-----------------------

When creating a new style there are two steps: define the style by creating a
`Style` object, and register your style with `register_style('my_style', my_style)`.
A good place to do that is in your `AppConfig.ready()`.

When defining a style you can start from an existing style, just start from
`base`, or totally from scratch. Totally from scratch is a lot more work, so
we recommend one of the other options if you can. Styles contain some basic
concepts:

- basing your style on one or more styles (you can base a style on a style object that isn't registered)
- assets
- `base_template`/`content_block`
- targeting a class for styling
- targeting a shortcut for styling

Things you will most likely want to target with a style are:

- tag
- attrs (especially `attrs__class`)
- template (try to avoid this as it can make upgrading iommi versions more brittle)





Basing on another style
~~~~~~~~~~~~~~~~~~~~~~~

To base a style on one or more styles, you pass the style objects positionally.
The order is significant as later styles can override previous definitions. A
simple example might be `my_style = Style(bootstrap)` which is just a new style
based on bootstrap. Note that style objects don't need to be registered to be
used like this, so you can use this to compose parts that make sense to keep
separate for readability or reuse.





Assets
~~~~~~

You can define assets on either the root (for common assets you want on all
pages, like the CSS framework), or on specific classes or shortcuts to
conditionally include them if that component is present on the page. Assets
from all components and the style root are collected and rendered in the
`<head>` tag.

Defining an asset on the root:


.. code-block:: python

    Style(
        root__assets__my_design_system_css=Asset.css(
            attrs=dict(
                href='https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css',
                integrity='sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh',
                crossorigin='anonymous',
            ),
        ),
    )


There is also a useful shortcut for JavaScript assets: `Asset.js(attrs__src='url')`.
You can put script and css literals (or anything really) there if you want:


.. code-block:: python

    Asset(tag='style', text='body { font-color: blue; }')


Adding an asset on a specific shortcut:


.. code-block:: python

    Style(
        Field__shortcuts__multi_choice__assets__foo=Asset.css(
            attrs__href='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/css/select2.min.css',
        ),
    )


Adding an asset on a specific class:


.. code-block:: python

    Style(
        Field__assets__foo=Asset.css(
            attrs__href='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/css/select2.min.css',
        ),
    )





base_template/content_block
~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default iommi uses `iommi/base.html` to render pages. For simple projects
this works very well, but for more complex sites you might need something
more complex. So you can define your base template in a style definition:


.. code-block:: python

    Style(
        base_template='base.html',
    )


If you do this, you will have to make sure to render the iommi assets in the
`<head>` tag:

.. code-block:: html

    {% for asset in assets.values %}
        {{ asset }}
    {% endfor %}

By default iommi will render the iommi page contents into the "content" block,
to override this you can define `content_block`:


.. code-block:: python

    Style(
        base_template='base.html',
        content_block='body',
    )





Targeting a class for styling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can apply style definitions via the class name:


.. code-block:: python

    Style(
        Field__attrs__class__foo=True,
    )


The style system will look at the full class hierarchy when it looks at what
definitions to apply. It will also match on the name of the class only,
the package name doesn't matter.





Targeting a shortcut for styling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can apply style definitions on shortcut names:


.. code-block:: python

    Style(
        MyClass__shortcuts__my_shortcut__attrs__class__foo=True,
    )


The style system will look at the full shortcut hierarchy when it looks at what
definitions to apply. So for example the shortcut `Field.choice_queryset` is
based on `Field.choice` so it will get the style configuration for
`Field.choice` in addition to the definitions for `Field.choice_queryset`.

The shortcut definitions are applied after the class definitions, as they
are more specific.

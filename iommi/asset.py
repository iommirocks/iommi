from iommi.fragment import Fragment
from iommi.shortcut import with_defaults


class Asset(Fragment):
    # language=rst
    """
    Class that describes an asset in iommi. Assets are meant to be the elements that you refer
    to in the HEAD of your document such as links to scripts, style sheets as well as
    inline scripts or css. But if necessary you can specify an arbitrary django template.

    Every :doc:`Part` can include the assets it needs. Similarly :doc:`Style` can include assets.
    When a part is rendered all assets are included in the head of the document.

    Because assets have names (:doc:`Everything has a name <philosophy>`), assets with the same name will overwrite
    each other, resulting in only one asset with a given name being rendered.
    """

    @classmethod
    @with_defaults(
        tag='script',
    )
    def js(cls, text=None, **kwargs):
        # language=rst
        """
        To use this shortcut, pass `attrs__src='/my_url_to_the.js'`

        Examples:

        .. code-block:: python

            Asset.js(
                attrs__src='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/js/select2.min.js',
            )

            Asset.js('window.foo = bar')
        """
        return cls(text, **kwargs)

    @classmethod
    @with_defaults(
        tag='link',
        attrs__rel='stylesheet',
    )
    def css(cls, text=None, **kwargs):
        # language=rst
        """
        To use this shortcut, pass `attrs__href='/my_url_to_the.css'`

        Examples:

        .. code-block:: python

            Asset.css(
                attrs__href='https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css',
                attrs__integrity='sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh',
                attrs__crossorigin='anonymous',
            )

            Asset.css('p { font-size: 18pt; }')
        """
        return cls(text, **kwargs)

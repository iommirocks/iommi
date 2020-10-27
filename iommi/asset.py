from typing import (
    Union,
)
from django.template import Template
from django.template.loader import get_template
from tri_declarative import (
    dispatch,
    setattr_path,
    Refinable,
)

from iommi.traversable import (
    EvaluatedRefinable,
    Traversable,
)


class Asset(Traversable):
    """
    Class that describes an asset in iommi. Assets are meant to be the elements that you refer
    to in the HEAD of your document such as links to scripts, style sheets as well as
    inline scripts or css. But if necessary you can specify an arbitrary django template.

    Every :doc:`Part` can include the assets it needs. Similarly :doc:`Style` can include assets.
    When a part is rendered all assets are included in the head of the document.

    Because assets have names (`Everything has a name`), assets with the same name will
    automatically get deduplicated.
    """
    name: str = Refinable()
    template: Union[str, Template, None] = Refinable()
    include: bool = EvaluatedRefinable()

    @dispatch(
        name=None,
        include=True,
        template=None,
    )
    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)

    def on_bind(self) -> None:
        super(Asset, self).on_bind()
        # Write the assets into the root part's all_assets, so that when that is rendered
        # all the assets are in one place
        # TODO: Is writing self crazy here?
        setattr_path(self.iommi_root().all_assets, self.iommi_name(), self)

    def __str__(self) -> str:
        if self.template:
            template = get_template(self.template) if isinstance(self.template, str) else self.template
            return template.render(self.get_context())
        else:
            # TODO What else should we support fragments?  Not immediately
            # clear how to that best as I can't import fragment in this module
            # but that would probably give us the nicest way to support
            # shortcuts like Asset.script_link and Asset.style_link or similar
            return "PROBLEM"
            pass

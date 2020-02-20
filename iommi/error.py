from tri_declarative import (
    dispatch,
    EMPTY,
)

from iommi.style import apply_style


class Errors(set):
    @dispatch(
        attrs=EMPTY,
    )
    def __init__(self, *, parent, attrs, errors=None, template=None):
        super(Errors, self).__init__(errors or [])
        self._parent = parent
        self.attrs = attrs
        self.template = template
        self.iommi_style = None
        apply_style(self)

    def __str__(self):
        return self.__html__()

    def __bool__(self):
        return len(self) != 0

    # noinspection PyUnusedLocal
    def __html__(self, *, context=None):
        if not self:
            return ''

        from iommi.page import Fragment
        return Fragment(
            tag='ul',
            attrs=self.attrs,
            template=self.template,
            children={
                f'error_{i}': Fragment(error, tag='li')
                for i, error in enumerate(self)
            },
        ).bind(parent=self._parent).__html__()

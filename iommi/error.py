from tri_declarative import (
    dispatch,
    EMPTY,
)

from iommi.reinvokable import reinvokable


class Errors:
    @dispatch(
        attrs=EMPTY,
    )
    @reinvokable
    def __init__(self, *, parent, attrs, template=None):
        self._parent = parent
        self.attrs = attrs
        self.template = template
        self.iommi_style = None

    def __str__(self):
        return self.__html__()

    def __bool__(self):
        # This function is needed because we want to be able to do {% if foo.errors %} in templates
        # noinspection PyProtectedMember
        return len(self._parent._errors) != 0

    def __html__(self):
        if not self:
            return ''

        from iommi import Fragment

        # We want the style system to treat this fragment like it's Errors, and
        # since it matches on the name of the class, inheritance here is enough
        class Errors(Fragment):
            pass

        # noinspection PyProtectedMember
        return (
            Errors(
                _name='error',
                tag='ul',
                attrs=self.attrs,
                template=self.template,
                children={
                    f'error_{i}': Fragment(
                        tag='li',
                        children__text=error,
                    )
                    for i, error in enumerate(sorted(self._parent._errors))
                },
            )
            .bind(parent=self._parent)
            .__html__()
        )

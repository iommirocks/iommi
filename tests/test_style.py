from iommi.style import (
    Style,
    apply_style_recursively,
)
from tri_declarative import (
    Refinable,
    RefinableObject,
    class_shortcut,
)


def test_style():
    class A(RefinableObject):
        foo = Refinable()
        bar = Refinable()

        @classmethod
        @class_shortcut(
            foo=1,
        )
        def shortcut1(cls, call_target, **kwargs):
            return call_target(**kwargs)

        def items(self):
            return dict(foo=self.foo, bar=self.bar)

    class B(A):
        @classmethod
        @class_shortcut(
            foo=2,
            bar=3,
            call_target__attribute='shortcut1'
        )
        def shortcut2(cls, call_target, **kwargs):
            return call_target(**kwargs)

    base = Style(
        A=dict(
            foo=1,
        ),
    )

    # TODO: use base here and remove redundant stuff
    overrides = Style(
        base,
        A=dict(
            shortcuts=dict(
                shortcut1__foo=4,
            ),
            foo=5,
            bar=6,
        ),
        B=dict(
            bar=7,
        ),
    )

    # First the unstyled case
    assert B().items() == dict(foo=None, bar=None)
    assert B.shortcut1().items() == dict(foo=1, bar=None)
    assert B.shortcut2().items() == dict(foo=2, bar=3)

    # Now let's add the style
    b = B()
    apply_style_recursively(overrides.component(b), b)
    assert b.items() == dict(foo=5, bar=7)

    b = B.shortcut1()
    assert overrides.component(b) == dict(foo=4, bar=7)
    assert b.__tri_declarative_shortcut_stack == ['shortcut1']
    apply_style_recursively(overrides.component(b), b)
    assert b.items() == dict(foo=4, bar=7)

    b = B.shortcut2()
    assert b.__tri_declarative_shortcut_stack == ['shortcut2', 'shortcut1']
    assert overrides.component(b) == dict(foo=4, bar=7)
    apply_style_recursively(overrides.component(b), b)
    assert b.items() == dict(foo=4, bar=7)

from tri.form.render import render_attrs


def test_render_attrs():
    assert render_attrs(None) == ''
    assert render_attrs({'foo': 'bar', 'baz': 'quux'}) == ' baz="quux" foo="bar"'


def test_render_class():
    assert render_attrs({'apa': True, 'bepa': '', 'cepa': None, 'class': dict(foo=False, bar=True, baz=True)}) == ' apa bepa="" class="bar baz"'


def test_render_attrs_non_standard_types():
    assert render_attrs({'apa': True, 'bepa': '', 'cepa': None, 'class': 'bar baz'}) == ' apa bepa="" class="bar baz"'


def test_render_style():
    assert render_attrs(
        dict(
            style=dict(
                foo='foo',
                bar='bar',
            )
        )
    ) == ' style="bar: bar; foo: foo"'

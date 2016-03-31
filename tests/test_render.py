from tri.form.render import render_attrs


def test_render_attrs():
    assert render_attrs(None) == ''
    assert render_attrs({'foo': 'bar', 'baz': 'quux'}) == ' baz="quux" foo="bar"'
    assert render_attrs({'apa': True, 'bepa': '', 'cepa': None, 'class': dict(foo=False, bar=True, baz=True)}) == ' apa bepa="" class="bar baz"'

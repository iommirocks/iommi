from iommi import Fragment


def test_basic_render():
    f = Fragment('foo').bind(request=None)
    assert f.__html__() == 'foo'


def test_render_multiple_children():
    f = Fragment('foo', children__bar='bar').bind(request=None)
    assert f.__html__() == 'foobar'


def test_nested():
    f = Fragment('foo', children__bar=Fragment('bar')).bind(request=None)
    assert f._is_bound
    assert f._bound_members.children._bound_members.bar._is_bound
    assert f.__html__() == 'foobar'


def test_tag():
    f = Fragment('foo', tag='div').bind(request=None)
    assert f.__html__() == '<div>foo</div>'


def test_attrs():
    f = Fragment(
        'foo',
        tag='div',
        attrs__class__foo=True,
        attrs__style__foo='foo',
        attrs__qwe='qwe',
    ).bind(request=None)
    assert f.__html__() == '<div class="foo" qwe="qwe" style="foo: foo">foo</div>'


def test_nested_attrs():
    f = Fragment(
        tag='div',
        children__text__tag='div',
        children__text__children__text='foo',
        children__text__attrs__class__foo=True,
        children__text__attrs__style__foo='foo',
        children__text__attrs__qwe='qwe',
    ).bind(request=None)
    assert f.__html__() == '<div><div class="foo" qwe="qwe" style="foo: foo">foo</div></div>'


def test_nested_attrs_lambda():
    f = Fragment(
        tag='div',
        children__text__tag='div',
        children__text__children__text='foo',
        children__text__attrs__qwe=lambda fragment, **_: fragment.tag,
    ).bind(request=None)
    assert f.__html__() == '<div><div qwe="div">foo</div></div>'


def test_nested_2():
    nested = Fragment('bar')
    f = Fragment('foo', children__bar=nested).bind(request=None)
    assert f._is_bound
    assert f._bound_members.children._bound_members.bar._is_bound
    assert not nested._is_bound
    assert f.__html__() == 'foobar'

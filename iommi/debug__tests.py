import pytest

from iommi import (
    Field,
    Form,
    Page,
    Table,
)
from iommi.debug import (
    dunder_path__format,
    filename_and_line_num_from_part,
    get_instantiated_at_info,
    local_debug_url_builder,
    should_ignore_frame,
    source_url_from_part,
)
from iommi.endpoint import find_target
from iommi.struct import Struct
from tests import debug_tests_stuff
from tests.helpers import req


def test_debug_tree_on_debug_false():
    class NestedPage(Page):
        foo = 'foo'

    class MyPage(Page):
        bar = 'bar'
        nested = NestedPage()

    root = MyPage().bind(request=req('get', **{'/debug_tree': '7'}))

    with pytest.raises(AssertionError):
        find_target(path='/debug_tree', root=root)


def test_debug_tree(settings):
    settings.DEBUG = True

    class NestedPage(Page):
        foo = 'foo'

        class Meta:
            @staticmethod
            def endpoints__fisk__func(**_):
                return None

    class MyPage(Page):
        bar = 'bar'
        nested = NestedPage()

    root = MyPage().bind(request=req('get', **{'/debug_tree': '7'}))
    target = find_target(path='/debug_tree', root=root)
    result = target.func(value='', **target.iommi_evaluate_parameters())

    assert isinstance(result, Table)
    tree = [', '.join([str(x.value) for x in cells]) for cells in result.cells_for_rows()]
    expected = """\
, , MyPage, True
endpoints, None, Endpoint, True
endpoints__debug_tree, debug_tree, Endpoint, True
endpoints__debug_templates_used, debug_templates_used, Endpoint, True
parts, None, Fragment, True
parts__bar, bar, Fragment, True
parts__bar__children, None, Fragment, True
parts__bar__children__text, None, str, False
parts__nested, nested, NestedPage, True
parts__nested__endpoints, None, Endpoint, True
parts__nested__endpoints__fisk, fisk, Endpoint, True
parts__nested__parts, None, Fragment, True
parts__nested__parts__foo, foo, Fragment, True
parts__nested__parts__foo__children, None, Fragment, True
parts__nested__parts__foo__children__text, None, str, False"""
    assert '\n'.join(tree) == expected


def test_debug_tree_crash_on_non_editable(settings):
    settings.DEBUG = True

    root = Form(fields__foo=Field.info(value='bar')).bind(request=req('get', **{'/debug_tree': '7'}))
    target = find_target(path='/debug_tree', root=root)
    result = target.func(value='', **target.iommi_evaluate_parameters())

    assert isinstance(result, Table)
    tree = [', '.join([str(x.value) for x in cells]) for cells in result.cells_for_rows()]
    expected = """\
, , Form, True
endpoints, None, Endpoint, True
endpoints__debug_tree, debug_tree, Endpoint, True
endpoints__debug_templates_used, debug_templates_used, Endpoint, True
fields, None, Field, True
fields__foo, foo, Field, True
fields__foo__endpoints, None, Endpoint, True
fields__foo__endpoints__config, config, Endpoint, True
fields__foo__endpoints__validate, validate, Endpoint, True
fields__foo__input, non_editable_input, Fragment, True
fields__foo__input__children, None, Fragment, True
fields__foo__input__children__text, None, NoneType, False
fields__foo__label, label, Fragment, True
fields__foo__non_editable_input, non_editable_input, Fragment, True
fields__foo__non_editable_input__children, None, Fragment, True
fields__foo__non_editable_input__children__text, None, NoneType, False"""
    assert '\n'.join(tree) == expected


def test_dunder_path__format():
    assert dunder_path__format(row=Struct(dunder_path=None)) == ''
    assert dunder_path__format(row=Struct(dunder_path='foo', name='foo')) == '<span class="full-path"></span>foo'
    assert (
        dunder_path__format(row=Struct(dunder_path='foo__bar', name='bar')) == '<span class="full-path">foo__</span>bar'
    )


def test_local_debug_url_builder(settings):
    settings.BASE_DIR = 'BASE_DIR'
    assert local_debug_url_builder('/foo.txt', None) == 'pycharm://open?file=/foo.txt'
    assert local_debug_url_builder('/foo.txt', 10) == 'pycharm://open?file=/foo.txt&line=10'
    assert local_debug_url_builder('foo.txt', 10) == 'pycharm://open?file=BASE_DIR/foo.txt&line=10'

    settings.IOMMI_DEBUG_URL_MAPPING = ['BASE_DIR', 'ANOTHER']
    assert local_debug_url_builder('foo.txt', 10) == 'pycharm://open?file=ANOTHER/foo.txt&line=10'


def test_should_ignore_frame():
    assert should_ignore_frame(Struct(f_globals={'__name__': 'iommi.admin.foo'}), {'syspath/foo'})
    assert should_ignore_frame(Struct(f_globals={'__name__': '_pydev_bundle.foo'}), {'syspath/foo'})
    assert should_ignore_frame(Struct(f_globals={'__name__': 'iommi.foo.bar'}), {'syspath/foo'})
    assert should_ignore_frame(Struct(f_globals={'__name__': 'iommi.declarative.foo.bar'}), {'syspath/foo'})
    assert should_ignore_frame(Struct(f_globals={'__name__': 'django.foo.bar'}), {'syspath/foo'})
    assert should_ignore_frame(
        Struct(f_globals={'__name__': 'qwe'}, f_code=Struct(co_filename='syspath/foo/bar/baz.py')), {'syspath/foo'}
    )
    assert should_ignore_frame(
        Struct(f_globals={'__name__': 'qwe'}, f_code=Struct(co_filename='<string>')), {'syspath/foo'}
    )
    assert should_ignore_frame(
        Struct(f_globals={'__name__': 'qwe'}, f_code=Struct(co_filename='foo/helpers/pycharm/asd')), {'syspath/foo'}
    )

    assert not should_ignore_frame(
        Struct(f_globals={'__name__': 'qwe'}, f_code=Struct(co_filename='my actual app')), {'syspath/foo'}
    )


def test_filename_and_line_num_from_part_empty_case():
    assert filename_and_line_num_from_part(part=Struct()) == (None, None)
    assert filename_and_line_num_from_part(part=Struct(_instantiated_at_info=('foo.py', 17))) == ('foo.py', 17)


def test_source_url_from_part(settings):
    settings.DEBUG = True

    # We need this instantiation of a Page to be outside the iommi code to get the right url
    filename = source_url_from_part(part=debug_tests_stuff.get_my_page())
    assert debug_tests_stuff.__file__ in filename

    # Make it trigger special code path that leads to the class definition
    p = debug_tests_stuff.MyPage()
    filename = source_url_from_part(part=p)
    assert __file__ in filename


def test_get_instantiated_at_info_base_case():
    frame = Struct(f_back=None)
    assert get_instantiated_at_info(frame) == (None, None)

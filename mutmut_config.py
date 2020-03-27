test_file_by_source_file = {
    'iommi/__init__.py': None,
    'iommi/_web_compat.py': None,  # need to skip this for now. many mutants here cause pytest-django to fail on load
    # 'iommi/_web_compat.py': 'tests/test_02_compat.py',  # TODO split web and db compat in tests
    'iommi/_db_compat.py': 'tests/test_02_compat.py tests/test_30_from_model.py',  # TODO split web and db compat in tests
    'iommi/action.py': 'tests/test_40_actions.py',
    'iommi/admin.py': 'tests/test_99_admin.py',
    'iommi/attrs.py': 'tests/test_05_attrs.py',
    'iommi/base.py': 'tests/test_04_base.py',
    'iommi/debug.py': None,
    'iommi/django_app.py': None,
    'iommi/docs.py': 'tests/test_99_docs.py',
    'iommi/endpoint.py': 'tests/test_06_endpoint.py',
    'iommi/error.py': 'tests/test_40_errors.py',
    'iommi/form.py': 'tests/test_40_forms.py tests/test_41_form_create_or_edit.py',
    'iommi/from_model.py': 'tests/test_30_from_model.py',
    'iommi/member.py': 'tests/test_15_member.py',
    'iommi/menu.py': 'tests/test_70_menu.py',
    'iommi/page.py': 'tests/test_20_pages.py tests/test_02_fragments.py',
    'iommi/part.py': 'tests/test_20_pages.py',
    'iommi/query.py': 'tests/test_50_query.py',
    'iommi/sort_after.py': 'tests/test_01_sort_after.py',
    'iommi/style.py': 'tests/test_10_style.py',
    'iommi/style_base.py': None,
    'iommi/style_test.py': None,
    'iommi/style_font_awesome_4.py': None,
    'iommi/style_bootstrap.py': None,
    'iommi/style_semantic_ui.py': None,
    'iommi/table.py': 'tests/test_60_table.py tests/test_61_table_sort.py',
    'iommi/traversable.py': 'tests/test_03_traversable.py',
    'iommi/profiling.py': None,
}


def init():
    pass


def pre_mutation(context, **_):
    spec = test_file_by_source_file[context.filename]
    if spec is None:
        context.skip = True
        return

    if '@functools.wraps' in context.current_source_line or '@dispatch' in context.current_source_line or '@abstractmethod' in context.current_source_line:
        context.skip = True
        return

    context.config.test_command += ' ' + spec

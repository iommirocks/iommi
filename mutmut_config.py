source_file_by_test_file = {
    'tests/test_00_reindent.py': 'tests/helpers.py',
    'tests/test_01_sort_after.py': 'iommi/sort_after.py',
    'tests/test_02_compat.py': 'iommi/_web_compat.py',  # TODO split web and db compat in tests
    'tests/test_03_traversable.py': 'iommi/traversable.py',
    'tests/test_04_base.py': 'iommi/base.py',
    'tests/test_05_attrs.py': 'iommi/attrs.py',
    'tests/test_06_endpoint.py': 'iommi/endpoint.py',
    'tests/test_10_style.py': 'iommi/style.py',
    'tests/test_15_member.py': 'iommi/member.py',
    'tests/test_20_pages.py': 'iommi/pages.py',
    'tests/test_30_from_model.py': 'iommi/from_model.py',
    'tests/test_40_forms.py': 'iommi/forms.py',
    'tests/test_40_errors.py': 'iommi/error.py',
    'tests/test_41_form_create_or_edit.py': 'iommi/form_create_or_edit.py',
    'tests/test_50_query.py': 'iommi/query.py',
    'tests/test_60_table.py': 'iommi/table.py',
    'tests/test_61_table_sort.py': 'iommi/table.py',
    'tests/test_99_admin.py': 'iommi/admin.py',
    'tests/test_99_docs.py': 'iommi/docs.py',
}

test_file_by_source_file = {v: k for k, v in source_file_by_test_file.items()}


def init():
    pass


def pre_mutation(context, **_):
    context.config.test_command += ' ' + test_file_by_source_file[context.filename]

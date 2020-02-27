from os import listdir

source_file_by_test_file = {
    'test_00_reindent.py': 'tests/helpers.py',
    'test_01_sort_after.py': 'iommi/sort_after.py',
    'test_02_compat.py': 'iommi/_web_compat.py',  # #TODO split web and db compat in tests
    'test_03_traversable.py': 'iommi/traversable.py',
    'test_04_base.py': 'iommi/base.py',
    'test_05_attrs.py': 'iommi/attrs.py',
    'test_06_endpoint.py': 'iommi/endpoint.py',
    'test_10_style.py': 'iommi/style.py',
    'test_15_member.py': 'iommi/member.py',
    'test_20_pages.py': 'iommi/pages.py',
    'test_30_from_model.py': 'iommi/from_model.py',
    'test_40_forms.py': 'iommi/forms.py',
    'test_41_form_create_or_edit.py': 'iommi/form_create_or_edit.py',
    'test_50_query.py': 'iommi/query.py',
    'test_60_table.py': 'iommi/table.py',
    'test_61_table_sort.py': 'iommi/table.py',
    'test_99_admin.py': 'iommi/admin.py',
    'test_99_docs.py': 'iommi/docs.py',
}

test_file_by_source_file = {v: k for k, v in source_file_by_test_file.items()}


def init():
    pass


def pre_mutation(context, **_):
    context.config.test_command += ' -k ' + test_file_by_source_file[context.filename].replace('.py', '')

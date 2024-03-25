import os


def init():
    pass


def pre_mutation(context, **_):
    if (
        '@functools.wraps' in context.current_source_line
        or '@dispatch' in context.current_source_line
        or '@abstractmethod' in context.current_source_line
        or '@reinvokable' in context.current_source_line
    ):
        context.skip = True
        return

    if '__tests.py' in context.filename:
        context.skip = True

    # run only relevant test module
    base_path = context.filename[: -len('.py')]
    base_name = os.path.split(base_path)[-1]
    module_test_file = f'{base_path}__tests.py'
    doc_test_file = f'docs/test_doc_{base_name}.py'

    if os.path.exists(module_test_file):
        context.config.test_command += ' ' + module_test_file

    if os.path.exists(doc_test_file):
        context.config.test_command += ' ' + doc_test_file

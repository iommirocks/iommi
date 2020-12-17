def init():
    pass


def pre_mutation(context, **_):
    if '@functools.wraps' in context.current_source_line or '@dispatch' in context.current_source_line or '@abstractmethod' in context.current_source_line or '@reinvokable' in context.current_source_line:
        context.skip = True
        return

    if '__tests.py' in context.filename:
        context.skip = True

    # run only relevant test module
    context.config.test_command += ' ' + context.filename[:-len('.py')] + '__tests.py'

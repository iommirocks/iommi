import os
from os.path import join
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django
django.setup()

from tests.helpers import create_iframe

from iommi.docs import generate_api_docs_tests
generate_api_docs_tests((Path(__file__).parent / 'docs').absolute())


# The rest of the docs

docs_dir = Path(__file__).parent / 'docs'


def write_rst_from_pytest():
    for source in docs_dir.glob('test_*.py'):
        target = source.parent / f'{source.stem.replace("test_doc__api_", "").replace("test_doc_", "")}.rst'

        with open(source) as source_f:
            with open(target, 'w') as target_f:

                rst_from_pytest(source_f, target_f, target)


def rst_from_pytest(source_f, target_f, target):
    state = 'import'
    prev_state = []
    func_name = None
    func_count = 0
    should_dedent = None
    write_code_block = False

    for i, line in enumerate(source_f.readlines(), start=1):
        print(source_f.name, i, func_name, state)
        stripped_line = line.strip()
        if state == 'import' and line.startswith('def test_'):  # not stripped_line!
            prev_state.append(state)
            state = 'py'
            func_name = line[len('def '):].partition('(')[0]
            func_count = 0
        elif stripped_line.startswith("# language=rst"):
            prev_state.append(state)
            state = 'starting rst'
        elif stripped_line in ('"""', "'''"):
            if state == 'starting rst':
                target_f.write('\n')
                prev_state.append(state)
                state = 'rst'
                should_dedent = line.startswith('    ')
            elif state == 'rst':
                state = prev_state.pop()
                assert state == 'starting rst'
                state = prev_state.pop() if prev_state else 'import'
                write_code_block = True
        elif stripped_line.startswith('# @test'):
            prev_state.append(state)
            state = 'only test'
        elif stripped_line.startswith('# @end'):
            state = prev_state.pop()
        else:
            if state == 'rst':
                if should_dedent and not line.startswith('    '):
                    should_dedent = False
                if should_dedent:
                    target_f.write(line[4:])
                else:
                    target_f.write(line)
            elif state == 'py':
                if stripped_line:
                    if write_code_block:
                        target_f.write('.. code-block:: python\n\n')
                        target_f.write('    ')  # guarantee empty code block
                        write_code_block = False

                if line.startswith('    ') or not stripped_line:
                    target_f.write(line)
            elif state == 'only test':
                if stripped_line.startswith('show_output(') or stripped_line.startswith('show_output_collapsed('):
                    name = join(target.stem, func_name)
                    if func_count:
                        name += str(func_count)
                    func_count += 1

                    target_f.write('.. raw:: html\n\n')
                    target_f.write('    ' + create_iframe(name, collapsed=stripped_line.startswith('show_output_collapsed')))


if __name__ == '__main__':
    write_rst_from_pytest()

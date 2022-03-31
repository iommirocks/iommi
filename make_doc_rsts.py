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

for source in docs_dir.glob('test_*.py'):
    target = source.parent / f'{source.stem.replace("test_doc__api_", "").replace("test_doc_", "")}.rst'

    with open(source) as source_f:
        with open(target, 'w') as target_f:
            state = 'import'
            func_name = None
            func_count = 0
            should_dedent = None
            write_code_block = False
            for line in source_f.readlines():
                stripped_line = line.strip()
                if line.startswith('def '):  # not stripped_line!
                    state = 'py'
                    func_name = line[len('def '):].partition('(')[0]
                    func_count = 0
                elif stripped_line.startswith("# language=rst"):
                    state = 'starting rst'
                elif stripped_line in ('"""', "'''"):
                    if state == 'starting rst':
                        target_f.write('\n')
                        state = 'rst'
                        should_dedent = line.startswith('    ')
                    elif state == 'rst':
                        state = 'py'
                        write_code_block = True
                elif stripped_line.startswith('# @test'):
                    state = 'only test'
                elif stripped_line.startswith('# @end'):
                    state = 'py'
                else:
                    if state == 'rst':
                        if should_dedent and line.startswith('    '):
                            target_f.write(line[4:])
                        else:
                            target_f.write(line)
                    elif state == 'py':
                        if stripped_line:
                            if write_code_block:
                                target_f.write('.. code-block:: python\n\n')
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


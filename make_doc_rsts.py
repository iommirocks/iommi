import os
from pathlib import Path

# API docs

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django
django.setup()

from iommi.docs import generate_api_docs_tests
generate_api_docs_tests((Path(__file__).parent / 'docs').absolute())


# The rest of the docs

docs_dir = Path(__file__).parent / 'docs'

for source in docs_dir.glob('test_*.py'):
    target = source.parent / f'{source.stem.replace("test_doc__api_", "").replace("test_doc_", "")}.rst'

    with open(source) as source_f:
        with open(target, 'w') as target_f:
            state = 'import'
            should_dedent = None
            write_code_block = False
            for line in source_f.readlines():
                stripped_line = line.strip()
                if line.startswith('def '):  # not stripped_line!
                    state = 'py'
                elif stripped_line.startswith("# language=rst"):
                    state = 'starting rst'
                elif stripped_line in ('"""', "'''"):
                    if state == 'starting rst':
                        target_f.write('\n')
                        state = 'rst'
                    elif state == 'rst':
                        state = 'py'
                        write_code_block = True
                elif stripped_line.startswith('# @test'):
                    state = 'only test'
                elif stripped_line.startswith('# @end'):
                    state = 'py'
                else:
                    if state == 'rst':
                        if should_dedent is None:
                            should_dedent = line.startswith('    ')

                        if should_dedent and len(line) >= 4:
                            if not line.startswith('    '):
                                should_dedent = False
                                target_f.write(line)
                            else:
                                target_f.write(line[4:])
                        else:
                            target_f.write(line)
                    elif state == 'py':
                        if stripped_line:
                            if write_code_block:
                                target_f.write('.. code-block:: python\n\n')
                                write_code_block = False

                        target_f.write(line)



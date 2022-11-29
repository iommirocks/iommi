import os
from os.path import join
from pathlib import Path
from textwrap import (
    dedent,
    indent,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django
django.setup()

from tests.helpers import create_iframe

from iommi.docs import generate_api_docs_tests
from iommi.struct import Struct
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
    blocks = []
    stack = []
    state_ = None

    def push(new_state, **kwargs):
        nonlocal state_
        nonlocal i
        assert state_ != 'only test', ('exited @test without @end', source_f.name, i)
        stack.append(new_state)
        blocks.append(Struct(state=new_state, lines=[], metadata=kwargs))
        state_ = new_state

    def pop():
        nonlocal state_
        stack.pop()
        state_ = stack[-1]
        blocks.append(Struct(state=state_, lines=[], metadata={}))

    def add_line(line):
        blocks[-1].lines.append(line)

    push('import')

    func_name = None
    func_count = 0

    for i, line in enumerate(source_f.readlines(), start=1):
        stripped_line = line.strip()
        if state_ in ('import', 'py') and line.startswith('def test_'):  # not stripped_line!
            func_name = line[len('def '):].partition('(')[0]
            push('py', func_name=func_name, func_count=0)
            func_count = 0
        elif stripped_line.startswith("# language=rst"):
            push('starting rst')
        elif stripped_line in ('"""', "'''"):
            if state_ == 'starting rst':
                # add_line('')
                pop()
                push('rst')
            elif state_ == 'rst':
                pop()
        elif stripped_line.startswith('# @test'):
            push('only test')
        elif stripped_line.startswith('# @end'):
            pop()
        elif state_ == 'py' and line.startswith('#'):  # not stripped_line! skip comments on the global level between functions
            continue
        else:
            if state_ == 'only test':
                if stripped_line.startswith('show_output(') or stripped_line.startswith('show_output_collapsed('):
                    name = join(target.stem, func_name)
                    if func_count:
                        name += str(func_count)
                    func_count += 1

                    blocks.append(Struct(state='raw', lines=[create_iframe(name, collapsed=stripped_line.startswith('show_output_collapsed'))], metadata={}))
            else:
                add_line(line)

    for b in blocks:
        b.text = dedent(''.join(b.lines)).strip()
        del b['lines']

    blocks = [x for x in blocks if x.text]

    for b in blocks:
        if b.state == 'rst':
            target_f.write(b.text)
        elif b.state == 'py':
            target_f.write('.. code-block:: python\n\n')
            target_f.write(indent(b.text, '    '))
        elif b.state == 'raw':
            target_f.write('.. raw:: html\n\n')
            target_f.write(indent(b.text, '    '))

        target_f.write('\n\n')


if __name__ == '__main__':
    write_rst_from_pytest()

import os
import sys
from glob import glob
from pathlib import Path

base_dir = Path(__file__).parent

os.makedirs(base_dir / '_generated_tests', exist_ok=True)

sys.path.insert(0, base_dir.parent)

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

from django import setup
setup()

from iommi.docs import generate_rst_docs

generate_rst_docs(str(base_dir))


def build_test_file_from_rst(filename):

    with open(filename) as f:
        lines = list(f.readlines())

    sections = [
        dict(header=None, code=[])
    ]

    current_section = sections[0]
    type_of_block = None
    for i, line in enumerate(lines):
        if line[:4] in ('~~~~', '====', '----', '^^^^'):
            header = lines[i-1].replace(':', '').replace('.', 'dot').replace("'", '').replace('&', '')
            current_section = dict(header=header, code=[])
            sections.append(current_section)
            type_of_block = None

        elif line.startswith('..'):
            type_of_block = line[2:].strip()

        elif line.startswith('    '):
            if type_of_block == 'code:: pycon':
                if line.strip().startswith('>>>'):
                    current_section['code'].append((line.replace('>>>', 'tmp ='), i))
                elif line.strip().startswith('...'):
                    current_section['code'].append((line.replace('...', ''), i))
                else:
                    current_section['code'].append(('    assert tmp == ' + line.strip(' '), i))
            elif type_of_block in ('code:: python', 'test'):
                current_section['code'].append((line, i))
            elif type_of_block == 'imports':
                current_section['code'].append((line[4:], i))  # 4: is to dedent one level

    func_trans = str.maketrans({
        '?': None,
        ' ': '_',
        '-': '_',
        '/': '_',
        ',': '_',
        '`': None,
    })

    with open(base_dir / '_generated_tests' / f'test_{filename.partition(os.path.sep)[-1].partition(".")[0]}.py', 'w') as f:
        setup = '''
from iommi import *
from iommi.admin import Admin
from django.urls import (
    include,
    path,
)
from django.db import models
from tests.helpers import req, user_req, staff_req
from docs.models import *
request = req('get')
'''.strip()
        f.write(setup)
        f.write('\n')

        current_line = setup.count('\n') + 3

        for section in sections:
            if section['header']:
                func_name = section['header'].strip().translate(func_trans).lower().partition('(')[0]
                def_line = f'\n\ndef test_{func_name}():\n'
                f.write(def_line)
                current_line += def_line.count('\n')
            else:
                func_name = None
            for line, line_number in section['code']:
                # This stuff is to make the line numbers align between .rst and test_*.py files.
                while line_number > current_line:
                    f.write('\n')
                    current_line += 1

                if line.strip() == 'return':
                    # A little hack to turn some return statements like "if not form.is_valid(): return" into non-covered
                    f.write(line.rstrip() + '  # pragma: no cover\n')
                else:
                    f.write(line)
                current_line += 1
            if not section['code'] and func_name:
                f.write('    pass\n')


for x in glob(str(base_dir / '*.rst')):
    build_test_file_from_rst(x)


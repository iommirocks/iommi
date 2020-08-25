import os
import sys
from glob import glob
from pathlib import Path

base_dir = Path(__file__).parent

os.makedirs(base_dir / '_generated_tests', exist_ok=True)

sys.path.insert(0, base_dir.parent)

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

from django.conf import settings
settings.configure()

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
            header = lines[i-1].replace(':', '').replace('.', 'dot').replace("'", '')
            current_section = dict(header=header, code=[])
            sections.append(current_section)
            type_of_block = None

        elif line.startswith('..'):
            type_of_block = line[2:].strip()

        elif line.startswith('    '):
            if type_of_block == 'code:: python-doctest':
                if line.strip().startswith('>>>'):
                    current_section['code'].append(line.replace('>>>', 'tmp ='))
                elif line.strip().startswith('...'):
                    current_section['code'].append(line.replace('...', ''))
                else:
                    current_section['code'].append('    assert tmp == ' + line.strip(' '))
            elif type_of_block in ('code:: python', 'test'):
                current_section['code'].append(line)
            elif type_of_block == 'imports':
                current_section['code'].append(line[4:])  # 4: is to dedent one level

    func_trans = str.maketrans({
        '?': None,
        ' ': '_',
        '-': '_',
        '/': '_',
        ',': '_',
        '`': None,
    })

    with open(base_dir / '_generated_tests' / f'test_{filename.partition(os.path.sep)[-1].partition(".")[0]}.py', 'w') as f:
        f.write('''
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
'''.lstrip())
        
        for section in sections:
            if section['header']:
                func_name = section['header'].strip().translate(func_trans).lower().partition('(')[0]
                f.write(f'\n\ndef test_{func_name}():\n')
            else:
                func_name = None
            f.writelines(section['code'])
            if not section['code'] and func_name:
                f.write('    pass\n')


for x in glob(str(base_dir / '*.rst')):
    build_test_file_from_rst(x)


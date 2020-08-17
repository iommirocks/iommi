from pathlib import Path


with open(Path(__file__).parent / 'howto.rst') as f:
    lines = list(f.readlines())

sections = [
    dict(header=None, code=[])
]

current_section = sections[0]
type_of_block = None
for i, line in enumerate(lines):
    if line.startswith('~~~~'):
        header = lines[i-1]
        current_section = dict(header=header, code=[])
        sections.append(current_section)

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
            current_section['code'].append(line.strip(' '))

func_trans = str.maketrans({
    '?': None,
    ' ': '_',
    '-': '_',
    '/': '_',
    ',': '_',
    '`': None,
})

with open(Path(__file__).parent / 'test_docs.py', 'w') as f:
    for section in sections:
        if section['header']:
            func_name = section['header'].strip().translate(func_trans).lower().partition('(')[0]
            f.write(f'\n\ndef test_{func_name}():\n')
        else:
            func_name = None
        f.writelines(section['code'])
        if not section['code'] and func_name:
            f.write('    pass\n')

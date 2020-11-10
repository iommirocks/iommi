import sys
from subprocess import run

assert __name__ == '__main__'

args = sys.argv[1:]
assert len(args) == 2
python_version, django_version = args

if python_version == 'pypy3':
    assert 'PyPy' in sys.version
else:
    assert python_version == '.'.join(map(str, sys.version_info[:2]))
    python_version = 'py' + python_version

tox_env = f"{python_version.replace('.', '')}-django{django_version.replace('.', '')}"

result = run(['tox', '-e', tox_env])
exit(result.returncode)

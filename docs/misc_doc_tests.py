from difflib import unified_diff
from pathlib import Path

current_dir = Path(__file__).parent

with open(current_dir / 'README.rst') as f:
    docs_readme = f.read()

with open(current_dir.parent / 'README.rst') as f:
    repo_readme = f.read()

# normalize the readmes:
docs_readme = docs_readme.replace('https://docs.iommi.rocks/en/latest/', '').replace(':doc:', '')
repo_readme = repo_readme.replace('https://docs.iommi.rocks/en/latest/', '').replace('.html>`_', '>`').replace('docs/', '')

exit_code = 0

for line in unified_diff(repo_readme.split('\n')[3:-6], docs_readme.split('\n')[4:], fromfile='README.rst', tofile='docs/README.rst'):
    print(line)
    exit_code = 1

exit(exit_code)

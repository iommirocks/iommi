from difflib import unified_diff
from pathlib import Path


def test_validate_readme():
    base_dir = Path(__file__).parent.parent

    with open(base_dir / 'docs' / 'README.rst') as f:
        docs_readme = f.read()

    with open(base_dir / 'README.rst') as f:
        repo_readme = f.read()

    # normalize the readmes:
    docs_readme = docs_readme.replace('https://docs.iommi.rocks/en/latest/', '').replace(':doc:', '')
    repo_readme = repo_readme.replace('https://docs.iommi.rocks/en/latest/', '').replace('.html>`_', '>`').replace('docs/', '')

    exit_code = 0

    for line in unified_diff(repo_readme.split('\n')[:-6], docs_readme.split('\n')[3:], fromfile='README.rst', tofile='docs/README.rst'):
        print(line)
        exit_code = 1

    assert exit_code == 0

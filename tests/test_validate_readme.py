from pathlib import Path

# The first badge is present in all three READMEs and marks the start of the
# shared content. Everything above it (logo + title) is rendered differently on
# GitHub (raw HTML), PyPI (rst image + title) and in the docs (a Sphinx title),
# so it's deliberately excluded from the comparison.
ANCHOR = '.. image:: https://img.shields.io/badge/Code_on-GitHub-black'


def _normalize(text):
    # Collapse runs of blank lines and strip leading/trailing whitespace so that
    # cosmetic blank-line differences don't cause spurious failures. The
    # meaningful content (badges, prose, code example, links) is still compared
    # exactly.
    lines = [line.rstrip() for line in text.strip().split('\n')]
    result = []
    for line in lines:
        if line == '' and result and result[-1] == '':
            continue
        result.append(line)
    return '\n'.join(result)


def _body(text):
    text = text[text.index(ANCHOR) :]
    # The repo/pypi versions end with a "Documentation" section the generated
    # docs version doesn't have.
    if 'Documentation\n---' in text:
        text = text[: text.index('Documentation\n---')]
    return _normalize(text)


def test_validate_readme():
    base_dir = Path(__file__).parent.parent

    # docs/README.rst is generated from docs/test_doc_README.py by the docs
    # tooling, which also runs the example in it as a test. This guards that the
    # GitHub README and the PyPI README stay in sync with it, so the homepage
    # examples are always up to date.
    docs_readme = (base_dir / 'docs' / 'README.rst').read_text().replace(':doc:', '')

    def normalize(text):
        # The repo/pypi versions link out to the published docs and reference
        # images by URL/path rather than via Sphinx roles and relative paths.
        return (
            text.replace('https://raw.githubusercontent.com/iommirocks/iommi/master/', '')
            .replace('https://docs.iommi.rocks//', '')
            .replace('.html>`_', '>`')
            .replace('docs/', '')
        )

    repo_readme = normalize((base_dir / 'README.rst').read_text())
    pypi_readme = normalize((base_dir / 'README_pypi.rst').read_text())

    assert _body(repo_readme) == _body(docs_readme)
    assert _body(pypi_readme) == _body(docs_readme)

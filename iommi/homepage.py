"""
Single source of truth for the code examples shown on the marketing homepage
(``homepage/index.html``).

The homepage is a hand authored static page, but its code examples must stay in
sync with the real iommi API just like the examples in the documentation do.
To get that guarantee:

- The canonical code for every snippet lives in :data:`SNIPPETS` below.
- ``tests/test_homepage.py`` executes each snippet against the live API, so a
  snippet that stops working (or has a typo) fails the test suite.
- :func:`generate` renders the snippets into ``homepage/index.html`` (replacing
  the contents of each ``<pre data-iommi-snippet="...">`` block) with syntax
  highlighting that matches the page's CSS. ``tests/test_homepage.py`` also
  asserts the committed file is up to date, so the page can never drift from the
  verified source.

Run ``make homepage`` (or ``python -m iommi.homepage``) to regenerate the page.
"""

import html
import io
import keyword
import tokenize
from pathlib import Path

HOMEPAGE_PATH = Path(__file__).parent.parent / 'homepage' / 'index.html'

# The page building example is shown in two places, so keep a single copy.
_PAGE = """\
from iommi import Table, Form, Page
from .models import Album

class AlbumPage(Page):
    class Meta:
        title = 'Albums'

    create_album = Form.create(auto__model=Album)
    albums = Table(auto__model=Album)
"""

SNIPPETS = {
    'hero': '# views.py\n' + _PAGE,
    'deep': """\
Table(
    auto__model=Album,
    columns__artist__filter__include=True,
    query__form__fields__artist__initial=
        lambda **_: Artist.objects.get(name='Dio'),
)
""",
    'filters': """\
class AlbumTable(Table):
    class Meta:
        auto__model = Album
        columns__artist__filter__include = True
        columns__year__filter__include = True
        bulk__delete__include = True
""",
    'install': '# 1) Install\n'
    'pip install iommi\n'
    '\n'
    '# 2) Add to INSTALLED_APPS\n'
    'INSTALLED_APPS = [\n'
    '    ...,\n'
    "    'iommi',\n"
    ']\n'
    '\n'
    '# 3) Add to MIDDLEWARE\n'
    'MIDDLEWARE = [\n'
    '    ...,\n'
    "    'iommi.middleware',\n"
    ']\n'
    '\n'
    '# 4) Build a page\n' + _PAGE + '\n'
    '# 5) Map it to a URL\n'
    'urlpatterns = [\n'
    "    path('album/', AlbumPage().as_view()),\n"
    ']\n',
}


def _classify(tokens, i):
    tok = tokens[i]
    if tok.type == tokenize.COMMENT:
        return 'comment'
    if tok.type == tokenize.STRING or tok.type == getattr(tokenize, 'FSTRING_START', -1):
        return 'string'
    if tok.type == tokenize.NAME:
        if keyword.iskeyword(tok.string):
            return 'keyword'
        # CamelCase (an upper case letter and at least one lower case letter) is a
        # class; ALL_CAPS names are constants (e.g. INSTALLED_APPS) and stay plain.
        if tok.string[0].isupper() and any(c.islower() for c in tok.string):
            return 'class-name'
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt is not None and nxt.type == tokenize.OP and nxt.string == '(':
            return 'function'
    return None


def highlight_python(code):
    """Render Python source to HTML using the homepage's syntax highlight classes."""
    tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    # Newlines and indentation are reconstructed from token positions, so the
    # structural tokens that carry no visible text are skipped entirely.
    skip = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.INDENT,
        tokenize.DEDENT,
    }
    out = []
    row, col = 1, 0
    for i, tok in enumerate(tokens):
        if tok.type in skip:
            continue
        (srow, scol), (erow, ecol) = tok.start, tok.end
        # Emit the whitespace gap between the previous token and this one verbatim.
        if srow > row:
            out.append('\n' * (srow - row))
            col = 0
        if scol > col:
            out.append(' ' * (scol - col))
        text = html.escape(tok.string, quote=False)
        css_class = _classify(tokens, i)
        out.append(f'<span class="{css_class}">{text}</span>' if css_class else text)
        row, col = erow, ecol
    return ''.join(out).strip('\n')


def _render_block(name):
    return f'<pre data-iommi-snippet="{name}"><code>{highlight_python(SNIPPETS[name])}\n</code></pre>'


def generate(text):
    """Return ``text`` with every ``<pre data-iommi-snippet="...">`` block regenerated."""
    import re

    def replace(match):
        name = match.group('name')
        if name not in SNIPPETS:
            raise ValueError(f'Unknown homepage snippet: {name!r}')
        return _render_block(name)

    return re.sub(
        r'<pre data-iommi-snippet="(?P<name>[^"]+)"><code>.*?</code></pre>',
        replace,
        text,
        flags=re.DOTALL,
    )


def main():
    text = HOMEPAGE_PATH.read_text()
    HOMEPAGE_PATH.write_text(generate(text))


if __name__ == '__main__':
    main()

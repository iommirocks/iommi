import re
from os import walk
from os.path import join
from pathlib import Path

from bs4 import BeautifulSoup

html_dir = Path(__file__).parent / 'docs'/ '_build' / 'html'

iommi_classes = {
    x for x in
    [f.stem for f in html_dir.glob('*.html')]
    if x[0].isupper()
}

url_by_symbol = {
    'Template': 'https://docs.djangoproject.com/en/dev/ref/templates/',
    'get_object_or_404': 'https://docs.djangoproject.com/en/dev/topics/http/shortcuts/#get-object-or-404',
    'path': 'https://docs.djangoproject.com/en/dev/topics/http/urls/#example',
    'decode_path': '/path.html',
    'decode_path_components': '/path.html',
    'register_path_decoding': '/path.html',
    'middleware': '/getting_started.html',
    'LAST': '/cookbook_tables.html#how-do-i-reorder-columns',
    'register_factory': '/registrations.html',
    'register_field_factory': '/registrations.html',
    'register_filter_factory': '/registrations.html',
    'register_column_factory': '/registrations.html',
    'register_cell_formatter': '/registrations.html',
    'register_style': '/registrations.html',
    'register_search_fields': '/registrations.html',
    'html': '/pages.html#html',
}

def build_link(t, url):
    return BeautifulSoup(f'<span class="n"><a href="{url}">{t}</span>', 'html.parser')

for root, dirs, files in walk(html_dir):
    for filename in files:
        if not filename.endswith('.html'):
            continue

        with open(join(root, filename)) as f:
            content = f.read()

        did_change = False

        # remove some extra newlines we can get from literalinclude
        if '\n</pre>' in content:
            did_change = True
            content = re.sub(r'\n+</pre>', '\n</pre>', content)

        soup = BeautifulSoup(content, 'html.parser')

        for symbol in soup.find_all('span', class_='n'):
            t = symbol.text
            if t in iommi_classes:
                symbol.replace_with(build_link(t, f'/{t}.html'))
                did_change = True
            elif t in url_by_symbol:
                symbol.replace_with(build_link(t, url_by_symbol[t]))
                did_change = True

        if did_change:
            with open(join(root, filename), 'w') as f:
                f.write(str(soup))

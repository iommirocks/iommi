from pathlib import Path

from django.conf import settings
from django.template.loader_tags import IncludeNode

from iommi._web_compat import format_html
from iommi.debug import src_debug_url_builder


def setup_code_finder():
    if not settings.DEBUG:
        return

    # IncludeNode monkey patch - output link to template location before each included template
    orig_include_render = IncludeNode.render

    def include_render(self, context):
        # Get the file path and line number from the node's origin and token
        link_html = ''
        if hasattr(self, 'origin') and self.origin:
            filename = self.origin.name
            # Token has a lineno attribute that gives us the line number
            line_number = self.token.lineno if hasattr(self, 'token') and hasattr(self.token, 'lineno') else 1

            # Create a PyCharm link
            link_html = format_html(
                '<!-- ## iommi-code-finder-URL ## {} ## {} -->',
                f'{Path(filename).name}:{line_number}',
                src_debug_url_builder(filename, line_number)
            )

        result = link_html + orig_include_render(self, context)
        return result

    IncludeNode.render = include_render

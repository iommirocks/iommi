from pathlib import Path

from django.conf import settings
from django.template.defaulttags import (
    ForNode,
    IfNode,
)
from django.template.loader_tags import IncludeNode
from django.templatetags.i18n import (
    BlockTranslateNode,
    TranslateNode,
)

from iommi._web_compat import format_html
from iommi.debug import src_debug_url_builder
from iommi.thread_locals import get_current_request


def setup_code_finder():
    if not settings.DEBUG:
        return

    for node_class in [IncludeNode, ForNode, IfNode, TranslateNode, BlockTranslateNode]:
        def debug_url_render(self, context, orig_render=node_class.render):
            orig_result = orig_render(self, context)
            request = get_current_request()
            if not request or '_iommi_code_finder' not in request.GET:
                return orig_result

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

            result = link_html + orig_result
            return result

        node_class.render = debug_url_render

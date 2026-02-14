from django.conf import settings
from django.http import HttpResponseRedirect

import iommi.style
from iommi import (
    LAST,
    Header,
    Page,
    html,
)
from iommi.base import items
from iommi.form import (
    Field,
    Form,
)
from iommi.style import validate_styles

# Use this function in your code to check that the style is configured correctly. Pass in all stylable classes in your system. For example if you have subclasses for Field, pass these here.
validate_styles()


class StyleSelector(Form):
    class Meta:
        @staticmethod
        def actions__submit__post_handler(request, form, **_):
            style = form.fields.style.value
            settings.IOMMI_DEFAULT_STYLE = style
            return HttpResponseRedirect(request.get_full_path())

        include = getattr(settings, 'IOMMI_REFINE_DONE_OPTIMIZATION', True) is False

    style = Field.choice(
        choices=[k for k, v in items(iommi.style._styles) if not v.internal],
        initial=lambda form, field, **_: getattr(settings, 'IOMMI_DEFAULT_STYLE', iommi.style.DEFAULT_STYLE),
    )


class ExamplesPage(Page):
    footer = html.div(
        html.hr(),
        html.a('iommi rocks!', attrs__href='http://iommi.rocks/'),
        StyleSelector(),
        after=LAST,
    )


class IndexPage(ExamplesPage):
    header = Header('Welcome to the iommi examples application')
    logo = html.img(
        attrs__src='https://docs.iommi.rocks/_static/logo_with_outline.svg',
        attrs__style__width='30%',
    )

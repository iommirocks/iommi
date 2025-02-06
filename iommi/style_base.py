from django.templatetags.static import static
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from iommi import Fragment
from iommi.asset import Asset
from iommi.debug import (
    endpoint__debug_templates_used,
    endpoint__debug_tree,
    iommi_debug_on,
)
from iommi.style import Style

select2_assets = dict(
    select2_js=Asset.js(attrs__src='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/js/select2.min.js'),
    select2_css=Asset.css(attrs__href='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/css/select2.min.css'),
)

select2_enhanced_forms = Style(
    internal=True,
    Field=dict(
        shortcuts=dict(
            multi_choice=dict(
                input__template='iommi/form/choice_select2.html',
                non_editable_input__attrs__class__select2_enhance=False,
                non_editable_input__attrs__disabled=True,
                assets=select2_assets,
                input__attrs__class__select2_enhance=True,
            ),
            checkboxes=dict(
                input__attrs__class__select2_enhance=False,
            ),
            choice_queryset=dict(
                input__template='iommi/form/choice_select2.html',
                non_editable_input__attrs__class__select2_enhance=False,
                non_editable_input__attrs__disabled=True,
                assets=select2_assets,
                input__attrs__class__select2_enhance=True,
                attrs__style={'min-width': '200px'},
            ),
        ),
    ),
)

iommi_js_init = Fragment(
    mark_safe(
        """\
<script>
    document.addEventListener("iommi.init.start", (event) => {
        event.detail.iommi.debug = true;
    });
</script>
"""
    ),
    include=lambda **_: iommi_debug_on(),
)

base = Style(
    internal=True,
    base_template='iommi/base.html',
    content_block='content',
    root=dict(
        endpoints__debug_tree=dict(
            include=lambda endpoint, **_: iommi_debug_on(),
            func=endpoint__debug_tree,
        ),
        endpoints__debug_templates_used=dict(
            include=lambda endpoint, **_: iommi_debug_on(),
            func=endpoint__debug_templates_used,
        ),
        assets=dict(
            jquery=Asset.js(
                attrs=dict(
                    src='https://code.jquery.com/jquery-3.4.1.js',
                    integrity='sha256-WpOohJOqMqqyKL9FccASB9O0KwACQJpFTUBLTYOVvVU=',
                    crossorigin='anonymous',
                ),
                after=-1,
            ),
            iommi_js=Asset.js(
                attrs=dict(
                    src=lambda **_: static('js/iommi.js'),
                ),
            ),
            iommi_js_init=iommi_js_init,
            iommi_scroll_js=Asset.js(
                attrs=dict(
                    src=lambda **_: static('js/iommi-scroll.js'),
                ),
            ),
            meta=Asset(
                mark_safe(
                    '''<meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" name="viewport">'''
                )
            ),
        ),
    ),
    Form=dict(
        shortcuts=dict(
            edit__actions__submit__display_name=gettext_lazy('Save'),
            create__actions__submit__display_name=gettext_lazy('Create'),
            delete__actions__submit__display_name=gettext_lazy('Delete'),
        ),
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__after=0,
                input__attrs__type='checkbox',
            ),
            choice=dict(
                input__template='iommi/form/choice.html',
                input__attrs__value=None,
                input__attrs__type=None,
            ),
            date__input__attrs__type='date',
            radio=dict(
                input__template='iommi/form/radio.html',
            ),
            checkboxes=dict(
                input__template='iommi/form/checkboxes.html',
                input__attrs__multiple=None,
            ),
            heading=dict(
                template='iommi/form/heading.html',
            ),
        ),
        non_editable_input=dict(
            attrs__disabled=lambda fragment, **_: True if fragment.tag in ('input', 'textarea') else None,
        ),
    ),
    Column=dict(
        shortcuts=dict(
            select=dict(
                header__attrs__title=gettext_lazy('Select all'),
            ),
        ),
        header__attrs__class__iommi_sort_header=lambda header, **_: header.url is not None,
    ),
    HeaderConfig=dict(
        tag='thead',
    ),
    Paginator=dict(
        show_always=False,
        template='iommi/table/paginator.html',
        item__tag='span',
        container__tag='div',
        active_item__tag='span',
        link__tag='a',
        link__attrs__class__iommi_page_link=True,
        attrs={
            "data-iommi-page-parameter": lambda paginator, **_: paginator.iommi_path,
            'aria-label': 'Pages',
        },
    ),
    Query=dict(
        template='iommi/query/form.html',
        advanced__template='iommi/query/advanced.html',
        assets__iommi_css=Asset.css(attrs__href=lambda **_: static('css/iommi.css')),
        form__attrs__class__iommi_filter=True,
    ),
    Actions=dict(
        tag='div',
        attrs__class__links=True,
    ),
    MenuItem=dict(
        a__tag='a',
        active_class='active',
    ),
    DebugMenu=dict(
        tag='nav',
        items_container__tag='ul',
        items_container__attrs__style={
            'list-style': 'none',
        },
        attrs__style={
            'position': 'fixed',
            'bottom': '-1px',
            'right': '-1px',
            'background': 'white',
            'border': '1px solid black',
            'z-index': '100',
        },
        attrs__class={
            'flex-column': False,
        },
    ),
    LiveEditPage__iommi_style='bootstrap',
)

base_enhanced_forms = Style(
    base,
    select2_enhanced_forms,
    internal=True,
)

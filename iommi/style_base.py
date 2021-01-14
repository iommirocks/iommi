from iommi.debug import (
    endpoint__debug_tree,
    iommi_debug_on,
)
from iommi.style import Style
from iommi.asset import Asset

select2_assets = dict(
    select2_js=Asset.js(
        attrs__src='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/js/select2.min.js',
    ),
    select2_css=Asset.css(
        attrs=dict(
            href='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/css/select2.min.css',
        )
    ),
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
        assets=dict(
            jquery=Asset.js(
                attrs=dict(
                    src='https://code.jquery.com/jquery-3.4.1.js',
                    integrity='sha256-WpOohJOqMqqyKL9FccASB9O0KwACQJpFTUBLTYOVvVU=',
                    crossorigin='anonymous',
                ),
                after=-1,
            ),
            axios=Asset.js(
                attrs=dict(
                    src='https://cdn.jsdelivr.net/npm/axios@0.21.0/dist/axios.min.js',
                    integrity='sha256-OPn1YfcEh9W2pwF1iSS+yDk099tYj+plSrCS6Esa9NA=',
                    crossorigin='anonymous',
                ),
                after=-1,
            ),
        ),
    ),
    Form=dict(
        template='iommi/form/form.html',
        actions_template='iommi/form/actions.html',
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__type='checkbox',
                template='iommi/form/row_checkbox.html',
            ),
            choice=dict(
                input__template='iommi/form/choice.html',
                input__attrs__value=None,
                input__attrs__type=None,
            ),
            multi_choice=dict(
                input__template='iommi/form/choice_select2.html',
                assets=select2_assets,
            ),
            choice_queryset=dict(
                input__template='iommi/form/choice_select2.html',
                assets=select2_assets,
            ),
            date__input__attrs__type='date',
            radio=dict(
                input__template='iommi/form/radio.html',
            ),
            heading=dict(
                template='iommi/form/heading.html',
            ),
        ),
        tag='div',
        input__attrs__type='text',
        input__tag='input',
        label__tag='label',
        non_editable_input__tag='span',
        help__attrs__class__helptext=True,
        help__tag='div',
    ),
    Column=dict(
        shortcuts=dict(
            select=dict(
                header__attrs__title='Select all',
            ),
        )
    ),
    Paginator=dict(
        show_always=False,
        template='iommi/table/paginator.html',
    ),
    Query=dict(
        template='iommi/query/form.html',
        advanced__template='iommi/query/advanced.html',
        assets__ajax_enhance__template='iommi/query/ajax_enhance.html',
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

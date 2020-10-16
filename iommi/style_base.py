from iommi import html
from iommi.style import Style

base = Style(
    base_template='iommi/base.html',
    content_block='content',
    assets=dict(
        jquery=html.script(
            attrs=dict(
                src='https://code.jquery.com/jquery-3.4.1.js',
                integrity='sha256-WpOohJOqMqqyKL9FccASB9O0KwACQJpFTUBLTYOVvVU=',
                crossorigin='anonymous',
            ),
            after=-1,
        ),
        select2_js=html.link(
            attrs__href='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/css/select2.min.css',
            attrs__rel='stylesheet',
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
            ),
            choice_queryset=dict(
                input__template='iommi/form/choice_select2.html',
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
)

from django.utils.translation import gettext_lazy

from iommi.asset import Asset
from iommi.debug import (
    endpoint__debug_tree,
    iommi_debug_on,
)
from iommi.style import Style
from iommi._web_compat import mark_safe

select2_assets = dict(
    select2_js=Asset.js(
        attrs__src='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/js/select2.min.js',
    ),
    select2_iommi_js=Asset.js(
        # language=js
        children__text=mark_safe('''
            document.addEventListener('readystatechange', () => {
                if (document.readyState === 'complete') {
                    iommi_init_all_select2();
                }
            });

            function iommi_init_all_select2() {
                $('.select2_enhance').each(function (_, x) {
                    iommi_init_select2(x);
                });
                // Second time is a workaround because the table might resize on select2-ification
                $('.select2_enhance').each(function (_, x) {
                    iommi_init_select2(x);
                });
            }

            function iommi_init_select2(elem) {
                let f = $(elem);
                let endpoint_path = f.attr('data-choices-endpoint');
                let multiple = f.attr('multiple') !== undefined;
                let options = {
                    placeholder: f.attr('data-placeholder'),
                    allowClear: true,
                    multiple: multiple
                };
                if (endpoint_path) {
                    options.ajax = {
                        url: function() {
                            return '?' + this.closest('form').serialize();
                        },
                        dataType: "json",
                        data: function (params) {
                            let result = {
                                page: params.page || 1
                            }
                            result[endpoint_path] = params.term || '';

                            return result;
                        }
                    }
                }
                f.select2(options);
                f.on('change', function(e) {
                    let element = e.target.closest('form');
                    // Fire a non-jquery event so that ajax_enhance.html gets the event
                    element.dispatchEvent(new Event('change'));
                });
            }
        ''')
    ),
    select2_css=Asset.css(
        attrs=dict(
            href='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/css/select2.min.css',
        )
    ),
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
            choice_queryset=dict(
                input__template='iommi/form/choice_select2.html',
                non_editable_input__attrs__class__select2_enhance=False,
                non_editable_input__attrs__disabled=True,
                assets=select2_assets,
                input__attrs__class__select2_enhance=True,
                attrs__style={
                    'min-width': '200px',
                }
            ),
        ),
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
        shortcuts=dict(
            edit__actions__submit__display_name=gettext_lazy('Save'),
            create__actions__submit__display_name=gettext_lazy('Create'),
            delete__actions__submit__display_name=gettext_lazy('Delete'),
        ),
        template='iommi/form/form.html',
        actions_template='iommi/form/actions.html',
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
            heading=dict(
                template='iommi/form/heading.html',
            ),
        ),
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

base_enhanced_forms = Style(
    base,
    select2_enhanced_forms,
    internal=True,
)

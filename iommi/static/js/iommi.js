
class IommiBase {
    debug = false;

    ajaxTimeout = 5000;

    historyStatePushedByUser = true;

    constructor(options) {
        for(let k in options){
            if(options.hasOwnProperty(k)) {
                 this[k] = options[k];
            }
        }
    }

    onDOMLoad() {
        document.dispatchEvent(
            new CustomEvent('iommi.init.start', {
                bubbles: true,
                detail: {iommi: this}
            })
        );

        const SELF = this;
        this.initAjaxPaginationAndSorting();
        document.querySelectorAll('.iommi_filter').forEach(
            form => SELF.enhanceFilterForm(form)
        );
        document.querySelectorAll('.iommi-table-container').forEach(
            container => SELF.enhanceTableContainer(container)
        );

        document.dispatchEvent(
            new CustomEvent('iommi.init.end', {
                bubbles: true,
                detail: {iommi: this}
            })
        );
    }

    onPopState(event) {
        // in extra method, so it can be overridden
        if (event.state && event.state.reloadOnUserAction) {
            if(this.historyStatePushedByUser) {
                // TODO in the future
                //  it might be better to rewrite this with element.iommi.reload()
                //  in await Promise.all() / Promise.allSettled() for all .iommi-table-container,
                //  so it just reloads all tables, not the whole page
                window.location.reload();
            } else {
                this.historyStatePushedByUser = true;  // reset to default
            }
        }
    }

    warnDeprecated(text) {
        if(this.debug) {
            console.warn(text);
        }
    }

    updateURL(params) {
        window.history.replaceState(null, null, `${window.location.pathname}?${params.toString()}`);
    }

    debounce(func, wait) {
        let timeout;

        return (...args) => {
            const fn = () => func.apply(this, args);

            clearTimeout(timeout);
            timeout = setTimeout(() => fn(), wait);
        };
    }

    async fetchJson(resource, options){
        const response = await fetch(resource, options);
        if(response.body) {
            return await response.json();
        }
        return {};
    }

    isAjaxAbort(err) {
        return err.name === 'AbortError';
    }

    getAbortController(element) {
        if(element.iommi && element.iommi.abortController) {
            return element.iommi.abortController;
        }
        return null;
    }

    resetAbortController(element) {
        const currentAbortController = this.getAbortController(element);
        if(currentAbortController !== null) {
            currentAbortController.abort();
        } else if(!element.iommi) {
            element.iommi = {};
        }
        const newAbortController = new AbortController();
        element.iommi.abortController = newAbortController;
        if (this.ajaxTimeout !== null) {
            setTimeout(() => newAbortController.abort(), this.ajaxTimeout);
        }
        return newAbortController;
    }

    async validateForm(params, form) {
        const errorsPath = form.getAttribute('data-iommi-errors');

        form.dispatchEvent(
            new CustomEvent('iommi.loading.start', {
                bubbles: true,
                detail: {urlSearchParams: params, endpoint: errorsPath}
            })
        );

        // it's better to do these outside of try-catch
        const ajaxURL = form.iommi.getAjaxValidationUrl.call(form, params, `&/${errorsPath}`);
        const ajaxOptions= {signal: this.resetAbortController(form).signal};

        try {
            const {global, fields} = await this.fetchJson(ajaxURL, ajaxOptions);

            const globalErrors = form.parentNode.querySelector('.iommi_query_error');
            if (global) {
                globalErrors.querySelectorAll('span').innerHTML = global.join(', ');
                globalErrors.classList.remove('hidden');
            } else {
                globalErrors.classList.add('hidden');
            }

            if (fields) {
                let fieldElement;
                Object.keys(fields).forEach(key => {
                    // Mark the field as invalid
                    fieldElement = form.querySelector(`[name="${key}"]`);
                    if(fieldElement) {
                        fieldElement.setCustomValidity(fields[key].join(', '));
                        fieldElement.reportValidity();
                    }
                });
            }
            form.dispatchEvent(
                new CustomEvent('iommi.loading.end', {
                    bubbles: true,
                    detail: {urlSearchParams: params, endpoint: errorsPath}
                })
            );
        } catch (err) {
            form.dispatchEvent(
                new CustomEvent('iommi.loading.end', {
                    bubbles: true,
                    detail: {urlSearchParams: params, endpoint: errorsPath}
                })
            );

            if (!this.isAjaxAbort(err)) {
                form.dispatchEvent(
                    new CustomEvent('iommi.error', {
                        bubbles: true,
                        detail: {
                            action: 'form.validation',
                            error: err,
                            urlSearchParams: params,
                            endpoint: errorsPath
                        }
                    })
                );

                console.error(err);
            }
        }
    }

    async updateTableContainer(container, params, extra){
        const tbodyPath = container.querySelector('[data-endpoint]').getAttribute(
            'data-endpoint'
        );

        this.callDeprecatedSpinner(true, container);  // deprecated, use event "iommi.loading.start" instead

        container.dispatchEvent(
            new CustomEvent('iommi.loading.start', {
                bubbles: true,
                detail: {...extra, urlSearchParams: params, endpoint: tbodyPath},
            })
        );

        // it's better to do these outside of try-catch
        let ajaxURL;
        if(extra.filterForm) {
            ajaxURL = extra.filterForm.iommi.getAjaxTbodyUrl.call(extra.filterForm, params, tbodyPath);
        } else {
            ajaxURL = this.getDefaultAjaxUrl(params, tbodyPath);
        }
        const ajaxOptions = {signal: this.resetAbortController(container).signal};

        try {
            const {html} = await this.fetchJson(ajaxURL, ajaxOptions);

            // We have to remove each child before setting innerHTML since disconnectedCallback
            // is not fired on the children using IE11
            let child = container.firstElementChild;
            while (child) {
                container.removeChild(child);
                child = container.firstElementChild;
            }

            const element = document.createRange().createContextualFragment(html);
            container.appendChild(element);

            container.dispatchEvent(
                new CustomEvent('iommi.element.populated', {
                    bubbles: true,
                    detail: {...extra, urlSearchParams: params, endpoint: tbodyPath},
                })
            );
        } catch (err) {
            if (!this.isAjaxAbort(err)) {
                if(extra.filterForm) {
                    extra.filterForm.querySelector('.iommi_query_error').innerHTML = err;
                }

                container.dispatchEvent(
                    new CustomEvent('iommi.error', {
                        bubbles: true,
                        detail: {
                            ...extra,
                            action: 'table.population',
                            error: err,
                            urlSearchParams: params,
                            endpoint: tbodyPath
                        },
                    })
                );
            }
        } finally {
            this.callDeprecatedSpinner(false, container);  // deprecated, use event "iommi.loading.end" instead
            container.dispatchEvent(
                new CustomEvent('iommi.loading.end', {
                    bubbles: true,
                    detail: {...extra, urlSearchParams: params, endpoint: tbodyPath},
                })
            );
        }
    }

    async queryPopulate(form) {
        const formData = new FormData(form);
        // TODO in the future
        //  new URLSearchParams(formData) will throw an error for file-inputs in filter forms,
        //  so delete them from formData
        const params = new URLSearchParams(formData);

        this.updateURL(params);
        await this.validateForm(params, form);

        const tableIommiID = form.getAttribute('data-iommi-id-of-table');
        let table = document.querySelector(`[data-iommi-id="${tableIommiID}"]`);

        await this.updateTableContainer(
            table.closest('.iommi-table-container'),
            params,
            {filterForm: form}
        )
    }

    hasSameData(prevData, newData) {
        return (
            [...newData].every(([key, value]) => prevData.get(key) === value) &&
            [...prevData].every(([key, value]) => newData.get(key) === value)
        );
    }

    enhanceFilterForm(form) {
        let table = document.querySelector(
            `[data-iommi-id="${form.getAttribute('data-iommi-id-of-table')}"]`
        )
        const container = table.closest('.iommi-table-container');

        form.setAttribute('autocomplete', 'off');
        const debouncedPopulate = this.debounce(this.queryPopulate, 400);

        let prevData = new FormData(form);
        const SELF = this;
        const onChange = e => {
            const formData = new FormData(form);
            if (SELF.hasSameData(prevData, formData)) {
                return;
            }
            prevData = formData;

            const fieldType = e.target.getAttribute('type');
            if (fieldType === 'file' && form.method === 'get') {
                // don't do anything
                // iommi endpoints are for GET only and files cannot be sent via GET
                // if you really need a file-input in the filter form, you have to add your own listener on change
            } else if (fieldType === 'text') {
                if (e.type === 'change') {
                    // change event fire when the input loses focus. We have already
                    // populated the form on the input event so ignore it
                    return;
                }
                SELF.callDeprecatedSpinner(true, container);  // deprecated, also it doesn't make sense to start spinner here imo
                // delay ajax request for free text
                debouncedPopulate(form, e.target);
            } else {
                // select2 elements have hidden inputs when they update GUI should respond immediately
                // same goes for checkboxes
                SELF.queryPopulate(form);
            }
        };
        ['change', 'input', 'switch-mode'].forEach(eventType => {
            form.addEventListener(eventType, onChange);
        });
        // reset event is being called just before the values get reset
        // timeout is probably the only way to run onChange after values get reset
        form.addEventListener('reset', (event) => {
            setTimeout(() => {
                $('.select2-hidden-accessible', form).val('');  // select2 does not react to reset
                onChange(event);
            }, 1);
        });

        const elements = form.parentNode.getElementsByClassName(
            'iommi_query_toggle_simple_mode'
        );
        if (elements.length > 0) {
            elements[0].addEventListener('click', () => {
                const event = new CustomEvent('switch-mode', {bubbles: true});
                form.dispatchEvent(event);
            });
        }

        Array.from(form.getElementsByClassName('select2')).forEach(s => {
            s.addEventListener('change', onChange);
        });

        form.querySelector('[data-iommi-filter-button]').remove();

        form.iommi = {
            getAjaxValidationUrl: function(params, endpoint) {
                return window.iommi.getDefaultAjaxUrl(params, endpoint);
            },

            getAjaxTbodyUrl: function(params, endpoint) {
                return window.iommi.getDefaultAjaxUrl(params, endpoint);
            }
        };
    }
    getDefaultAjaxUrl(params, endpoint) {
        return `?${params.toString()}&${endpoint}`;
    }

    /**
     * simple live event listener (similar to jquery.on)
     */
    static addLiveEventListener(eventType, elementQuerySelector, callback) {
        document.addEventListener(eventType, function (event) {
            const qs = document.querySelectorAll(elementQuerySelector);
            if (qs) {
                let el = event.target, index = -1;
                while (el && ((index = Array.prototype.indexOf.call(qs, el)) === -1)) {
                    el = el.parentElement;
                }

                if (index > -1) {
                    callback.call(el, event);
                }
            }
        });
    }

    initAjaxPaginationAndSorting() {
        const SELF = this;
        IommiBase.addLiveEventListener(
            'click',
            '.iommi-table-container .iommi_page_link, .iommi-table-container .iommi_sort_header a',
            function (event) {
                const container = this.closest('.iommi-table-container');
                const href = this.getAttribute('href');
                let hrefSearchParams;
                try {
                    hrefSearchParams = new URL(href).searchParams;
                } catch {
                    hrefSearchParams = new URLSearchParams(href);
                }
                SELF.historyStatePushedByUser = false;
                window.history.pushState({reloadOnUserAction: true},'', href);
                SELF.updateTableContainer(container, hrefSearchParams, {pageLink: this});
                container.scrollIntoView({behavior: 'smooth'});
                event.preventDefault();
                return false;
            }
        );
    }

    enhanceTableContainer(container) {
        container.iommi = {
            // so people can easily reload tables after long afk or on websocket message or just with setTimeout
            reload: function() {
                let url = new URL(window.location.href);
                return window.iommi.updateTableContainer(container, url.searchParams, {isReload: true});
            },
        };
    }

    // in case someone has overridden iommi_show_spinner
    callDeprecatedSpinner(isLoading, container) {
        if(!iommi_show_spinner.iommiOriginal) {
            this.warnDeprecated('iommi_show_spinner is deprecated, use events "iommi.loading.start" and "iommi.loading.end" instead');
            iommi_show_spinner(isLoading, container);
        }
    }
}


class IommiSelect2 {
    constructor() {
        const SELF = this;
        document.addEventListener('iommi.element.populated', (event) => {
            SELF.initAll(event.target);
        });
    }

    onCompleteReadyState() {
        this.initAll();
    }

    initAll(parent, selector, extra_options) {
        const SELF = this;
        if(!parent) {
            parent = document;
        }
        if(!selector) {
            selector = '.select2_enhance';
        }
        $(selector, parent).each(function (_, x) {
            SELF.initOne(x, extra_options);
        });
        // Second time is a workaround because the table might resize on select2-ification
        $(selector, parent).each(function (_, x) {
            SELF.initOne(x, extra_options);
        });
    }

    initOne(elem, extra_options) {
        let f = $(elem);
        let endpointPath = f.attr('data-choices-endpoint');
        let multiple = f.attr('multiple') !== undefined;
        let options = {
            placeholder: f.attr('data-placeholder'),
            allowClear: true,
            multiple: multiple
        };
        if (endpointPath) {
            options.ajax = {
                url: function () {
                    let form = this.closest('form');

                    // Url with query string can usually be max 4kB.
                    // If you have big forms, then your select2's can stop working, so you have to
                    // turn off sending form data to the server with:
                    // form.attrs={'data-select2-full-state': ''}
                    let fullState = form.attr('data-select2-full-state');
                    // but if you need some values for some field.choices, you can specify the names of the fields,
                    // that you need to be sent to the server, with:
                    // field.input__attrs={'data-select2-partial-state': json.dumps(['artist', 'year'])}
                    let partialState = f.data('select2-partial-state');
                    if (fullState === undefined) {
                        fullState = 'true';
                    }
                    if(partialState) {
                        return '?' + $(partialState.map(function(value) {return `[name="${value}"]`}).join(', '), form).serialize();
                    } else if (fullState === 'true') {
                        return '?' + form.serialize();
                    } else {
                        return '';
                    }
                },
                dataType: 'json',
                data: function (params) {
                    let result = {
                        page: params.page || 1
                    }
                    result[endpointPath] = params.term || '';

                    return result;
                }
            }
        }
        if(extra_options) {
            $.extend(options, extra_options);
        }
        f.select2(options);
        f.on('change', function (e) {
            let element = e.target.closest('form');
            // Fire a non-jquery event so that enhanceFilterForm gets the event
            element.dispatchEvent(new Event('change'));
        });
    }
}

// TODO should this be somehow conditioned? so people can create their own extended instance?
window.iommi = new IommiBase({
    select2: new IommiSelect2()
});

document.addEventListener('DOMContentLoaded', () => {
    window.iommi.onDOMLoad();
});

window.addEventListener('popstate', function(event) {
    window.iommi.onPopState(event);
});

document.addEventListener('readystatechange', () => {
    if (document.readyState === 'complete') {
        window.iommi.select2.onCompleteReadyState();
    }
});


// deprecated functions - for backward compatibility only

function iommi_update_URL(params) {
    window.iommi.warnDeprecated('iommi_update_URL is deprecated, use iommi.updateURL instead');
    return window.iommi.updateURL(params);
}

function iommi_debounce(func, wait) {
    window.iommi.warnDeprecated('iommi_debounce is deprecated, use iommi.debounce instead');
    return window.iommi.debounce(func, wait);
}

async function iommi_validate_form(params, form) {
    window.iommi.warnDeprecated('iommi_validate_form is deprecated, use iommi.validateForm instead');
    return window.iommi.validateForm(params, form);
}

async function iommi_query_populate(form) {
    window.iommi.warnDeprecated('iommi_query_populate is deprecated, use iommi.queryPopulate instead');
    return window.iommi.queryPopulate(form);
}

function iommi_has_same_data(prevData, newData) {
    window.iommi.warnDeprecated('iommi_has_same_data is deprecated, use iommi.hasSameData instead');
    return window.iommi.hasSameData(prevData, newData);
}

function iommi_enhance_form(form) {
    window.iommi.warnDeprecated('iommi_enhance_form is deprecated, use iommi.enhanceFilterForm instead');
    return window.iommi.enhanceFilterForm(form);
}

function iommi_show_spinner(isLoading, container) {
    window.iommi.warnDeprecated('iommi_show_spinner is deprecated, use events "iommi.loading.start" and "iommi.loading.end" instead');
}
iommi_show_spinner.iommiOriginal = true;

function iommi_init_all_select2() {
    window.iommi.warnDeprecated('iommi_init_all_select2 is deprecated, use iommi.select2.initAll instead');
    return window.iommi.select2.initAll();
}

function iommi_init_select2(elem) {
    window.iommi.warnDeprecated('iommi_init_select2 is deprecated, use iommi.select2.initOne instead');
    return window.iommi.select2.initOne(elem);
}

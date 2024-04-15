class IommiBase {
    debug = false;

    ajaxTimeout = 5000;

    historyStatePushedByUser = true;

    constructor(options) {
        for (let k in options) {
            if (options.hasOwnProperty(k)) {
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
            if (this.historyStatePushedByUser) {
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

    /**
     * returns iommi table container or null if none found
     * @param  {Element} element filter form or any other element with data-iommi-id-of-table attribute or any element inside container
     * @return {(Element|null)} container element or null
     */
    getContainer(element) {
        if (element.hasAttribute('data-iommi-id-of-table')) {
            return document.querySelector(
                `.iommi-table-container[data-iommi-id="${element.getAttribute('data-iommi-id-of-table')}"]`
            );
        }
        return element.closest(".iommi-table-container");
    }

    debounce(func, wait) {
        let timeout;

        return (...args) => {
            const fn = () => func.apply(this, args);

            clearTimeout(timeout);
            timeout = setTimeout(() => fn(), wait);
        };
    }

    async fetchJson(resource, options) {
        const response = await fetch(resource, options);
        if (response.body) {
            return await response.json();
        }
        return {};
    }

    isAjaxAbort(err) {
        return err.name === 'AbortError';
    }

    getAbortController(element) {
        if (element.iommi && element.iommi.abortController) {
            return element.iommi.abortController;
        }
        return null;
    }

    resetAbortController(element) {
        const currentAbortController = this.getAbortController(element);
        if (currentAbortController !== null) {
            currentAbortController.abort();
        } else if (!element.iommi) {
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
        const ajaxOptions = {signal: this.resetAbortController(form).signal};

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
                    if (fieldElement) {
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

    async updateTableContainer(container, params, extra) {
        const tbodyPath = container.getAttribute('data-endpoint');

        container.dispatchEvent(
            new CustomEvent('iommi.loading.start', {
                bubbles: true,
                detail: {...extra, urlSearchParams: params, endpoint: tbodyPath},
            })
        );

        // it's better to do these outside of try-catch
        let ajaxURL;
        if (extra.filterForm) {
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
                if (extra.filterForm) {
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

        // we need to preserve filters from other table filters and sorting
        let params;
        try {
            params = new URL(window.location.href).searchParams;
        } catch {
            params = new URLSearchParams(window.location.href);
        }

        // first remove from URL params all that belongs to this filter
        const deleteParams = new Set();
        for (const [key, value] of params) {
            if (typeof form.elements[key] !== "undefined") {
                deleteParams.add(key);
            }
        }
        for (let key of deleteParams) {
            params.delete(key);
        }

        // append to URL params only applied filters
        for (const [key, value] of formData) {
            if (value && !(value instanceof File)) {
                // new URLSearchParams(formData) would throw an error for files
                params.append(key, value);
            }
        }

        const container = this.getContainer(form);

        // remove "page" for this table to always jump to the first page after filtering
        const paginator = container.querySelector('[data-iommi-page-parameter]');
        if (paginator) {
            params.delete(paginator.getAttribute('data-iommi-page-parameter'));
        }

        window.history.replaceState(null, null, `${window.location.pathname}?${params.toString()}`);

        await this.validateForm(params, form);

        await this.updateTableContainer(container, params, {filterForm: form});
    }

    hasSameData(prevData, newData) {
        return (
            [...newData].every(([key, value]) => prevData.get(key) === value) &&
            [...prevData].every(([key, value]) => newData.get(key) === value)
        );
    }

    enhanceFilterForm(form) {
        const container = this.getContainer(form);

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
            getAjaxValidationUrl: function (params, endpoint) {
                return window.iommi.getDefaultAjaxUrl(params, endpoint);
            },

            getAjaxTbodyUrl: function (params, endpoint) {
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
                window.history.pushState({reloadOnUserAction: true}, '', href);
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
            reload: function () {
                let url = new URL(window.location.href);
                return window.iommi.updateTableContainer(container, url.searchParams, {isReload: true});
            },
        };
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
        if (!parent) {
            parent = document;
        }
        if (!selector) {
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
                    if (partialState) {
                        return '?' + $(partialState.map(function (value) {
                            return `[name="${value}"]`
                        }).join(', '), form).serialize();
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
        if (extra_options) {
            $.extend(options, extra_options);
        }
        f.select2(options);
        f.on('change', function (e) {
            let element = e.target.closest('form');
            // Fire a non-jquery event so that enhanceFilterForm gets the event
            if (element) {
                element.dispatchEvent(new Event('change'));
            }
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

window.addEventListener('popstate', function (event) {
    window.iommi.onPopState(event);
});

document.addEventListener('readystatechange', () => {
    if (document.readyState === 'complete') {
        window.iommi.select2.onCompleteReadyState();
    }
});

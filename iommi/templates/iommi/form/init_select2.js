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
            url: function () {
                let form = this.closest('form');

                let full_state = form.attr('data-select2-full-state');
                if (full_state === undefined) {
                    full_state = "true";
                }
                if (full_state === 'true') {
                    return '?' + form.serialize();
                }
                else {
                    return "";
                }
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
    f.on('change', function (e) {
        let element = e.target.closest('form');
        // Fire a non-jquery event so that ajax_enhance.js gets the event
        element.dispatchEvent(new Event('change'));
    });
}

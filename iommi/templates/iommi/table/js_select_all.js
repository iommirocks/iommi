
// Polyfill for closest() on IE11. Remove when we drop support for IE11.

if (!Element.prototype.matches) {
    Element.prototype.matches =
        Element.prototype.msMatchesSelector ||
        Element.prototype.webkitMatchesSelector;
}

if (!Element.prototype.closest) {
    Element.prototype.closest = function (s) {
        var el = this;

        do {
            if (Element.prototype.matches.call(el, s)) return el;
            el = el.parentElement || el.parentNode;
        } while (el !== null && el.nodeType === 1);
        return null;
    };
}

// End polyfill for IE11


function iommi_table_js_select_all(base, has_paginator) {
    var table = base.closest('table');
    var tbody = table.querySelector('tbody');
    // Select all checkboxes on this page
    Array.prototype.forEach.call(tbody.querySelectorAll('.checkbox'), function (el, i) {
        el.click();
    });

    // If there are multiple pages
    if (has_paginator) {
        // If we haven't done so already offer to select everything
        if (tbody.querySelector('.select_all_pages_q') === null) {
            tbody.querySelector('tr').insertAdjacentHTML('beforebegin', '<tr><td colspan="99" style="text-align: center" class="select_all_pages_q">All items on this page are selected. <a onclick="iommi_table_js_select_all_pages(this)" href="#">Select all items</a></td></tr>'
            )
        } else {
            // Otherwise the select all button was hit again (and nothing should be selected)
            // Hide the select everything again.
            var row_with_select_all = tbody.querySelector('.select_all_pages_q').closest('tr');
            row_with_select_all.parentNode.removeChild(row_with_select_all);
            var form = base.closest('form');
            form.querySelector('.all_pks').value = 0;
        }
    }
}

function iommi_table_js_select_all_pages(base) {
    var form = base.closest('form');
    var tbody = form.querySelector('tbody');
    tbody.querySelector('.select_all_pages_q').textContent = 'All items selected';
    form.querySelector('.all_pks').value = 1;
}

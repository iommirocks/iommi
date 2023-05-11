// {% load i18n %}

function iommi_register_query_toggles(query_iommi_dunder_path) {
    var base = document.getElementById('iommi_' + query_iommi_dunder_path);
    var q = document.getElementById('iommi_' + query_iommi_dunder_path + '_query');
    var help = base.getElementsByClassName('iommi_query_toggle_help')[0];

    function toggle_simple_advanced() {
        var toggle_simple_mode = base.getElementsByClassName("iommi_query_toggle_simple_mode")[0];
        var simple = base.getElementsByClassName("iommi_query_form_simple")[0];
        var adv = base.getElementsByClassName("iommi_query_form_advanced")[0];
        if (toggle_simple_mode.getAttribute('data-advanced-mode') === 'simple') {
            q.value = q.getAttribute('data-query');
            toggle_simple_mode.setAttribute('data-advanced-mode', 'advanced');
            adv.style.display = '';
            simple.style.display = 'none';
            toggle_simple_mode.innerHTML = '{% blocktrans %}Switch to basic search{% endblocktrans %}';
            help.style.display = '';
        }
        else {
            q.setAttribute('data-query', q.value);
            q.value = '';
            toggle_simple_mode.setAttribute('data-advanced-mode', 'simple');
            adv.style.display = 'none';
            simple.style.display = '';
            toggle_simple_mode.innerHTML = '{% blocktrans %}Switch to advanced search{% endblocktrans %}';
            help.style.display = 'none';
            if (help.style.display === '') {
                toggle_help();
            }
        }
        return false;
    }

    function toggle_help() {
        var icon = help.querySelector('i');
        var help_text = base.getElementsByClassName('iommi_query_help')[0];
        if (icon.classList.contains('fa-chevron-down')) {
            help_text.style.display = '';
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
            help.querySelector('span').innerText = '{% blocktrans %}Hide help{% endblocktrans %}';
        }
        else {
            help_text.style.display = 'none';
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
            help.querySelector('span').innerText = '{% blocktrans %}Show help{% endblocktrans %}';
        }
    }

    if (q.getAttribute('data-query') !== '') {
        toggle_simple_advanced();
    }

    base.getElementsByClassName("iommi_query_toggle_simple_mode")[0].addEventListener('click', toggle_simple_advanced);
    help.addEventListener('click', toggle_help);
}

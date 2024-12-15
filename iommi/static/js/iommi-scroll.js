document.addEventListener('readystatechange', (event) => {
    if (document.readyState === 'complete') {
        let prev_focused = sessionStorage.getItem('focused_element');
        if (prev_focused) {
            prev_focused = document.getElementById(`${prev_focused}`);
            if (prev_focused) {
                prev_focused.focus();
            }
        } else {
            let auto_focus = document.getElementsByClassName('.auto_focus');
            if (auto_focus.length) {
                auto_focus[0].focus();
            }
        }

        if (document.querySelector('.secondary_menu')) {
            document.querySelector('body').classList.add('has_secondary_menu');
        } else if (document.querySelector('.dryft-menu')) {
            document.querySelector('body').classList.add('has_primary_menu');
        }

        window.addEventListener("beforeunload", function (e) {
            sessionStorage.setItem('scroll_pos', window.scrollY);
            sessionStorage.setItem('scroll_url', window.location.href);
            sessionStorage.setItem('focused_element', document.activeElement.id);
        });
    }
});

document.addEventListener("DOMContentLoaded", function (event) {
    let scroll_pos = sessionStorage.getItem('scroll_pos');
    if (scroll_pos) {
        if (sessionStorage.getItem('scroll_url') === window.location.href) {
            window.scrollTo(0, scroll_pos);
        }
        sessionStorage.removeItem('scroll_pos');
    }
});

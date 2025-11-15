function docReady(fn) {
    // see if DOM is already available
    if (document.readyState === "complete" || document.readyState === "interactive") {
        // call on next available tick
        setTimeout(fn, 1);
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
}

function resizeIFrameToFitContent( frame ) {
    frame.width  = frame.contentWindow.document.body.scrollWidth;
    frame.height = frame.contentWindow.document.body.scrollHeight;
}

docReady(function() {
    var iframes = document.querySelectorAll("iframe");
    for( var i = 0; i < iframes.length; i++) {
        iframes[i].addEventListener('load', function(e) {
            resizeIFrameToFitContent(e.target);
        });
    }

    // Expand the components section, if nothing else is expanded.
   if (!document.querySelectorAll(".sidebar-tree .toctree-checkbox:checked").length) {
       document.querySelector("a[href='components.html']").parentElement.querySelector("input.toctree-checkbox[type='checkbox']").checked = true;
   }
});

function toggle(id, source) {
    let e = document.getElementById(id);
    if (e.style.display === 'none') {
        e.style.display = '';
        source.innerText = '▼ Hide result';
        resizeIFrameToFitContent(e);
    }
    else {
        e.style.display = 'none';
        source.innerText = '► Show result';
    }
}

function scrollToLocationHash() {
    const link = document.querySelector(`a[href="${window.location.hash}"]`);
    if (!window.location.hash) {
        return;
    }
    const section = document.querySelector(window.location.hash);
    if(section) {
        if(link) {
            // right panel with links to anchors has its own scrollbar,
            // so when the link is at the end, scroll it to view too
            link.scrollIntoView();
        }
        section.scrollIntoView();
    }
}

docReady(function() {
    scrollToLocationHash();
    document.querySelectorAll("iframe").forEach(iframe => {
        iframe.addEventListener('load', () => {
            scrollToLocationHash();
        });
    });
});

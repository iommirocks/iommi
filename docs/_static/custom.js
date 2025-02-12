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

    // Always expand the first section
    let x = document.getElementById('toctree-checkbox-1');
    if (!x.checked) {
        x.click();
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

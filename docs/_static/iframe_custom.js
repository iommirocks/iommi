document.addEventListener("click", handler, true);

function handler(e) {
    e.stopPropagation();
    e.preventDefault();
}


function toggle_name_information_boxes() {
    // Remove any existing info boxes
    for (const p of document.querySelectorAll('.iommi-name-information_boxes')) {
        p.remove();
    }

    let body = document.getElementsByTagName('body')[0];
    if (body.classList.contains('show_structure')) {
        body.classList.remove('show_structure');
        return
    }
    else {
        body.classList.add('show_structure');
    }

    let anchorId = 0;

    for (let p of document.querySelectorAll('[data-iommi-type]')) {
        // Create unique anchor name for this element
        const anchorName = `--iommi-anchor-${anchorId++}`;
        p.style.anchorName = anchorName;

        // Create info box
        const infoBox = document.createElement('div');
        infoBox.className = 'iommi-name-information_boxes';
        infoBox.style.setProperty('--anchor-name', anchorName);

        const typeAttr = p.getAttribute('data-iommi-type') || 'unknown';
        const typeSpan = document.createElement('span');
        typeSpan.className = 'iommi-type';
        typeSpan.textContent = typeAttr;
        infoBox.appendChild(typeSpan);

        const pathSpan = document.createElement('span');
        pathSpan.className = 'iommi-path';

        if (typeAttr === 'Container') {
            pathSpan.textContent = '<Container is configurable only via the Style>';
        } else {
            const pathAttr = p.getAttribute('data-iommi-path');
            if (pathAttr) {
                pathSpan.textContent = pathAttr;
            }
        }

        if (pathSpan.textContent) {
            infoBox.appendChild(pathSpan);
        }

        // Append info box to document body
        document.body.appendChild(infoBox);
    }
}

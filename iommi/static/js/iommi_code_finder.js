
function findPrecedingIommiComment(targetNode) {
    // First check for comments inside the target node itself
    if (targetNode.childNodes) {
        for (let i = 0; i < targetNode.childNodes.length; i++) {
            const child = targetNode.childNodes[i];
            if (child.nodeType === 8 && child.textContent.includes('## iommi-code-finder-URL ##')) {
                return child;
            }
        }
    }

    // Recursively search up the tree
    let currentNode = targetNode;

    while (currentNode && currentNode !== document.documentElement) {
        // Check all previous siblings and their descendants
        let sibling = currentNode.previousSibling;
        while (sibling) {
            if (sibling.nodeType === 8 && sibling.textContent.includes('## iommi-code-finder-URL ##')) {
                return sibling;
            }
            // Check descendants of the sibling
            const commentInSibling = findCommentInDescendants(sibling);
            if (commentInSibling) {
                return commentInSibling;
            }
            sibling = sibling.previousSibling;
        }

        // Move up to parent node
        currentNode = currentNode.parentNode;
    }

    return null;
}

function findCommentInDescendants(node) {
    if (!node || node.nodeType === 3) { // Skip text nodes
        return null;
    }

    // Use a tree walker to search descendants
    const walker = document.createTreeWalker(
        node,
        NodeFilter.SHOW_COMMENT,
        {
            acceptNode: function(comment) {
                if (comment.textContent.includes('## iommi-code-finder-URL ##')) {
                    return NodeFilter.FILTER_ACCEPT;
                }
                return NodeFilter.FILTER_SKIP;
            }
        },
        false
    );

    // Find the last matching comment in descendants
    let lastComment = null;
    let comment;
    while (comment = walker.nextNode()) {
        lastComment = comment;
    }

    return lastComment;
}

function createIommiCodeFinderOverlay() {
    // Remove any existing overlay
    const existing = document.getElementById('iommi-code-finder-overlay');
    if (existing)
        existing.remove();

    // Create overlay container
    const overlay = document.createElement('div');
    overlay.id = 'iommi-code-finder-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.9);
        color: #ffeb3b;
        padding: 12px 16px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        z-index: 100000;
        min-width: 400px;
        max-width: 600px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        border: 1px solid #ffeb3b;
        pointer-events: none;
        transition: opacity 0.2s;
    `;

    document.body.appendChild(overlay);

    // Create highlight element
    const highlight = document.createElement('div');
    highlight.id = 'iommi-code-finder-highlight';
    highlight.style.cssText = `
        position: absolute;
        background: rgba(255, 235, 59, 0.2);
        border: 2px solid #ffeb3b;
        pointer-events: none;
        z-index: 99999;
        transition: all 0.1s;
        display: none;
    `;
    document.body.appendChild(highlight);

    let lastTarget = null;
    let currentUrl = null;

    // Handle clicks when overlay is active
    document.addEventListener('click', (e) => {
        // Allow normal clicks when shift is held
        if (e.shiftKey)
            return;

        // If we have a current URL, open it
        if (currentUrl) {
            e.preventDefault();
            e.stopPropagation();
            window.open(currentUrl, '_blank');
        }
    }, true); // Use capture phase to intercept before other handlers

    document.addEventListener('mousemove', (e) => {
        const target = e.target;
        if (target === lastTarget || target === overlay || target === highlight)
            return;

        lastTarget = target;

        const comment = findPrecedingIommiComment(target);

        if (comment) {
            // Parse the comment
            const match = comment.textContent.match(/## iommi-code-finder-URL ##\s*(.+?)\s*##\s*(.+?)(?:\s*##|$)/);

            if (match) {
                const shortName = match[1].trim();
                currentUrl = match[2].trim();

                // Update overlay content
                overlay.style.opacity = '1';
                overlay.innerHTML = `
                    <div style="margin-top: 8px; padding-top:">
                        ${escapeHtml(shortName)}<br>
                        <strong>Element:</strong> &lt;${target.tagName.toLowerCase()}&gt;
                        ${target.id ? `<br><strong>ID:</strong> ${escapeHtml(target.id)}` : ''}
                        <br><br>
                        <em style="color: #4CAF50;">Click to open link</em><br>
                        <em style="color: #888; font-size: 11px;">Hold Shift for normal clicks<br>Go back to exit</em>
                    </div>
                `;

                // Highlight the target element
                const rect = target.getBoundingClientRect();
                highlight.style.left = rect.left + window.scrollX + 'px';
                highlight.style.top = rect.top + window.scrollY + 'px';
                highlight.style.width = rect.width + 'px';
                highlight.style.height = rect.height + 'px';
                highlight.style.display = 'block';

                // document.body.style.cursor = 'pointer';
            }
        } else {
            // No debug comment found
            currentUrl = null;
            overlay.style.opacity = '0.7';
            overlay.innerHTML = `
                <strong style="color: #f44336;">✗ No code link found</strong><br>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #555;">
                    <strong>Element:</strong> &lt;${target.tagName.toLowerCase()}&gt;
                    ${target.id ? `<br><strong>ID:</strong> ${escapeHtml(target.id)}` : ''}
                    <br><br>
                    <em style="color: #888; font-size: 11px;">Hold Shift for normal clicks<br>Go back to exit</em>
                </div>
            `;
            highlight.style.display = 'none';

            document.body.style.cursor = '';
        }
    });

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Clean up on scroll
    window.addEventListener('scroll', () => {
        if (highlight.style.display === 'block' && lastTarget) {
            const rect = lastTarget.getBoundingClientRect();
            highlight.style.left = rect.left + window.scrollX + 'px';
            highlight.style.top = rect.top + window.scrollY + 'px';
        }
    });

    // Return references to overlay and highlight for external activation
    return {overlay, highlight};
}
window.addEventListener('load', () => {
    // Initialize the overlay only if _iommi_code_finder parameter is present
    const urlParams = new URLSearchParams(window.location.search);
    const {overlay, highlight} = createIommiCodeFinderOverlay();
    // Activate the code finder system immediately
    overlay.style.opacity = '1';
    overlay.innerHTML = '<strong>Iommi Code Finder Active</strong><br>Move cursor to inspect elements<br><em style="color: #888; font-size: 11px;">Hold Shift for normal clicks<br>Go back to exit</em>';
});

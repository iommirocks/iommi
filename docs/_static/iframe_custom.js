document.addEventListener("click", handler, true);

function handler(e) {
    e.stopPropagation();
    e.preventDefault();
}

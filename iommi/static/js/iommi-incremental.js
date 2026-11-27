(function () {
    const TRIGGER = Object.freeze({
        LOAD_MORE: 'load_more',
        INFINITE_SCROLL: 'infinite_scroll',
        LOAD_MORE_THEN_INFINITE_SCROLL: 'load_more_then_infinite_scroll'
    });

    class IommiIncremental {
        constructor(iommi) {
            this.iommi = iommi;

            document.addEventListener('iommi.element.populated', event => this.initialize(event.target));
            document.addEventListener('click', event => this.warnBeforePageNavigation(event), true);
            ['input', 'change'].forEach(type => {
                document.addEventListener(type, event => this.markUnsavedEdit(event));
            });

            this.initialize(document);
        }

        initialize(root) {
            root.querySelectorAll('[data-iommi-incremental]').forEach(control => {
                if (control.iommiIncremental) return;
                control.iommiIncremental = {loading: false, observer: null};

                control.querySelector('[data-iommi-incremental-load-more]').addEventListener('click', () => this.load(control));
                control.querySelector('[data-iommi-incremental-retry]').addEventListener('click', () => this.load(control));

                const automatic = control.dataset.iommiIncremental === TRIGGER.INFINITE_SCROLL ||
                    control.dataset.iommiActiveMode === TRIGGER.INFINITE_SCROLL;
                const button = control.querySelector('[data-iommi-incremental-load-more]');
                button.hidden = automatic && this.observe(control);
            });
        }

        observe(control) {
            const Observer = window.IntersectionObserver;
            const sentinel = control.querySelector('[data-iommi-incremental-sentinel]');
            if (typeof Observer !== 'function' || !sentinel) return false;

            const state = control.iommiIncremental;
            try {
                state.observer = new Observer(entries => {
                    if (entries.some(entry => entry.isIntersecting)) this.load(control);
                }, {rootMargin: `0px 0px ${window.innerHeight}px 0px`});
                state.observer.observe(sentinel);
                return true;
            } catch (_error) {
                state.observer = null;
                return false;
            }
        }

        pageUrl(control) {
            const url = new URL(window.location.href);
            url.searchParams.set(
                `${control.dataset.iommiPageParameter}_incremental_start`,
                control.dataset.iommiStartPage
            );
            url.searchParams.set(control.dataset.iommiIncrementalEndpoint, control.dataset.iommiNextCursor);
            return url;
        }

        isCurrent(control, container, generation) {
            return control.isConnected && container.contains(control) &&
                generation === container.iommiIncrementalGeneration;
        }

        startLoading(control) {
            const state = control.iommiIncremental;
            state.loading = true;
            if (state.observer) state.observer.disconnect();

            control.setAttribute('aria-busy', 'true');
            const status = control.querySelector('[data-iommi-incremental-status]');
            status.textContent = status.dataset.iommiLoadingText;
            control.querySelector('[data-iommi-incremental-load-more]').disabled = true;
            control.querySelector('[data-iommi-incremental-retry]').hidden = true;
        }

        finishLoading(control) {
            control.iommiIncremental.loading = false;
            control.removeAttribute('aria-busy');
            control.querySelector('[data-iommi-incremental-load-more]').disabled = false;
        }

        async requestPage(control) {
            const response = await fetch(this.pageUrl(control), {
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        }

        appendPage(control, container, items, result) {
            const oldPaginator = control.closest('[data-iommi-incremental-paginator]');
            const activeMode = control.dataset.iommiIncremental === TRIGGER.LOAD_MORE_THEN_INFINITE_SCROLL
                ? TRIGGER.INFINITE_SCROLL : control.dataset.iommiActiveMode;

            items.insertAdjacentHTML('beforeend', result.html);
            oldPaginator.insertAdjacentHTML('afterend', result.paginator_html);
            const newPaginator = oldPaginator.nextElementSibling;
            oldPaginator.remove();

            const next = newPaginator.querySelector('[data-iommi-incremental]');
            if (next && activeMode) next.dataset.iommiActiveMode = activeMode;

            items.dispatchEvent(new CustomEvent('iommi.element.populated', {
                bubbles: true,
                detail: {incremental: true}
            }));
            this.initialize(container);
        }

        showFailure(control, error) {
            const status = control.querySelector('[data-iommi-incremental-status]');
            status.textContent = status.dataset.iommiErrorText;
            control.querySelector('[data-iommi-incremental-load-more]').hidden = true;
            control.querySelector('[data-iommi-incremental-retry]').hidden = false;
            control.dispatchEvent(new CustomEvent('iommi.error', {
                bubbles: true,
                detail: {action: 'table.incremental', error}
            }));
        }

        async load(control) {
            const state = control.iommiIncremental;
            if (state.loading || !control.isConnected) return;

            const container = this.iommi.getContainer(control);
            const items = container && container.querySelector('[data-iommi-incremental-items]');
            if (!items) return;
            const generation = container.iommiIncrementalGeneration;

            this.startLoading(control);
            try {
                const result = await this.requestPage(control);
                if (this.isCurrent(control, container, generation)) {
                    this.appendPage(control, container, items, result);
                }
            } catch (error) {
                if (this.isCurrent(control, container, generation)) this.showFailure(control, error);
            } finally {
                this.finishLoading(control);
            }
        }

        markUnsavedEdit(event) {
            const container = this.iommi.getContainer(event.target);
            if (container && container.querySelector('[data-iommi-edit-table-row]')) {
                container.iommiIncrementalDirty = true;
            }
        }

        warnBeforePageNavigation(event) {
            const link = event.target.closest('[data-iommi-incremental-page-link]');
            if (!link) return;
            const container = this.iommi.getContainer(link);
            if (!container || !container.querySelector('[data-iommi-edit-table-row]')) return;
            const hasVirtualRow = container.querySelector('[data-iommi-edit-table-row][data-pk^="-"]');
            if (!container.iommiIncrementalDirty && !hasVirtualRow) return;

            const paginator = link.closest('[data-iommi-incremental-paginator]');
            if (!window.confirm(paginator.dataset.iommiUnsavedWarning)) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        }
    }

    function bind(iommi) {
        if (!iommi.incremental) iommi.incremental = new IommiIncremental(iommi);
    }

    // The event covers either import order during page load; the flag covers a late asset.
    document.addEventListener('iommi.init.end', event => bind(event.detail.iommi));
    if (window.iommi && window.iommi.initialized) bind(window.iommi);
})();

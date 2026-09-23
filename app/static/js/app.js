/**
 * LegalLens AI — Application Orchestrator
 *
 * Responsibilities:
 *  - Hash-based SPA routing
 *  - Document state management (localStorage persistence)
 *  - API call orchestration
 *  - AI status polling
 *  - Event delegation
 */
import { api }        from './api.js';
import { components } from './components.js';
import { views }      from './views.js';

class App {
    constructor() {
        this.root         = document.getElementById('app-root');
        this.currentDocId = localStorage.getItem('legallens_current_doc') || null;
        this.document     = null;       // current Document metadata
        this.cache        = new Map();  // per-doc analysis cache
        this.aiConfigured = null;       // tri-state: null = unknown, true, false
    }

    async init() {
        // Dismiss disclaimer banner
        document.getElementById('dismiss-disclaimer')?.addEventListener('click', (ev) => {
            ev.currentTarget.closest('.legal-disclaimer-banner')?.remove();
        });

        // Hash-based routing
        window.addEventListener('hashchange', () => this.route());

        // Check AI status (non-blocking)
        this._updateAiStatus();

        // Initial render
        await this.route();
    }

    // ─── AI Status ────────────────────────────────────────────────────────────

    async _updateAiStatus() {
        const dot  = document.getElementById('ai-status-dot');
        const text = document.getElementById('ai-status-text');
        if (!dot || !text) return;

        try {
            const status = await api.getStatus();
            this.aiConfigured = status.ai_configured;
            if (status.ai_configured) {
                dot.className  = 'ai-status-dot ready';
                text.textContent = 'AI Ready';
            } else {
                dot.className  = 'ai-status-dot fallback';
                text.textContent = 'Fallback Mode';
            }
        } catch {
            dot.className  = 'ai-status-dot fallback';
            text.textContent = 'Status Unknown';
        }
    }

    // ─── Router ───────────────────────────────────────────────────────────────

    async route() {
        const hash = window.location.hash.slice(1) || '/';

        // Sync nav active state
        document.querySelectorAll('.nav-link').forEach(link => {
            const href = link.getAttribute('href') || '';
            link.classList.toggle('active', href === `#${hash.split('/')[1] ? '/' + hash.split('/')[1] : '/'}`);
        });

        // Toggle workspace nav item
        const wsNav = document.getElementById('nav-workspace');
        if (wsNav) {
            if (this.currentDocId) {
                wsNav.classList.remove('hidden');
            } else {
                wsNav.classList.add('hidden');
            }
        }

        try {
            if (hash === '/') {
                await this._renderHome();
            } else if (hash === '/workspace' || hash.startsWith('/workspace/')) {
                const tab = hash.split('/')[2] || 'summary';
                await this._renderWorkspace(tab);
            } else if (hash === '/compare') {
                await this._renderCompare();
            } else {
                this.root.innerHTML = `<div class="page-container"><p class="text-muted">Page not found.</p></div>`;
            }
        } catch (err) {
            console.error('[App] Route error:', err);
            this.root.innerHTML = `
                <div class="page-container">
                    <div class="card card-body text-center" style="color:var(--danger)">
                        Something went wrong: ${components.escapeHtml(err.message)}
                    </div>
                </div>`;
        }
    }

    // ─── Home ─────────────────────────────────────────────────────────────────

    async _renderHome() {
        // Show quick skeleton
        this.root.innerHTML = `<div class="page-container">${components.loader('Loading…')}</div>`;

        let docs = [];
        try {
            const data = await api.listDocuments();
            docs = data.documents || [];
        } catch { /* non-fatal */ }

        const { html, bindEvents } = views.home(docs);
        this.root.innerHTML = `<div class="page-container">${html}</div>`;
        bindEvents(this);
    }

    // ─── Workspace ────────────────────────────────────────────────────────────

    async _renderWorkspace(tab) {
        if (!this.currentDocId) {
            window.location.hash = '/';
            return;
        }

        // Load document if needed
        if (!this.document || this.document.id !== this.currentDocId) {
            try {
                this.document = await api.getDocument(this.currentDocId);
            } catch {
                // Document gone (e.g. server restarted) — go home
                this._clearCurrentDoc();
                window.location.hash = '/';
                return;
            }
        }

        // Render the shell with sidebar + empty content
        this.root.innerHTML = `
            <div class="page-container">
                ${views.workspaceShell(this.document, tab)}
            </div>`;

        // Wire workspace-level buttons
        document.getElementById('btn-new-doc')?.addEventListener('click', () => {
            this._clearCurrentDoc();
            window.location.hash = '/';
        });
        document.getElementById('btn-delete-doc')?.addEventListener('click', () => {
            this.handleDelete(this.currentDocId);
        });

        // Render tab content
        const contentArea = document.getElementById('workspace-content');
        contentArea.innerHTML = components.loader(`Loading ${tab}…`);

        try {
            await this._renderTab(tab, contentArea);
        } catch (err) {
            contentArea.innerHTML = `
                <div class="card card-body text-center">
                    <p style="color:var(--danger)">✕ ${components.escapeHtml(err.message)}</p>
                    <button class="btn btn-secondary mt-3" onclick="window.location.reload()">Retry</button>
                </div>`;
        }
    }

    async _renderTab(tab, contentArea) {
        const docId    = this.currentDocId;
        const isDemo   = this.document?.filename?.includes('DEMO') || false;

        switch (tab) {
            case 'summary': {
                const data       = await this._cached('summary', () => api.getSummary(docId));
                const isFallback = data._metadata?.analysis_mode === 'fallback';
                contentArea.innerHTML = views.summary(data, isFallback, isDemo);
                this._bindRetryBtn(contentArea, 'summary');
                break;
            }
            case 'clauses': {
                const data       = await this._cached('clauses', () => api.getClauses(docId));
                const isFallback = data._metadata?.analysis_mode === 'fallback';
                contentArea.innerHTML = views.clauses(data.clauses, isFallback);
                this._bindRetryBtn(contentArea, 'clauses');
                break;
            }
            case 'risks': {
                const data       = await this._cached('risks', () => api.getRisks(docId));
                const isFallback = data._metadata?.analysis_mode === 'fallback';
                contentArea.innerHTML = views.risks(data.review_flags, data.obligations, isFallback);
                this._bindRetryBtn(contentArea, 'risks');
                break;
            }
            case 'qa': {
                const { html, bindEvents } = views.qa(docId);
                contentArea.innerHTML = html;
                bindEvents(this);
                break;
            }
            case 'checklist': {
                const data       = await this._cached('checklist', () => api.getChecklist(docId));
                const isFallback = data._metadata?.analysis_mode === 'fallback';
                contentArea.innerHTML = views.checklist(data.checklist, isFallback);
                views.checklistBindEvents();
                this._bindRetryBtn(contentArea, 'checklist');
                break;
            }
            case 'lawyer': {
                const data       = await this._cached('lawyer', () => api.getLawyerQuestions(docId));
                const isFallback = data._metadata?.analysis_mode === 'fallback';
                contentArea.innerHTML = views.lawyer(data.questions, isFallback);
                this._bindRetryBtn(contentArea, 'lawyer');
                break;
            }
            default:
                contentArea.innerHTML = `<p class="text-muted">Unknown section.</p>`;
        }
    }

    _bindRetryBtn(area, tab) {
        area.querySelector('#retry-ai-btn')?.addEventListener('click', () => {
            // Bust cache and re-render to try AI again
            this.cache.delete(tab);
            const contentArea = document.getElementById('workspace-content');
            if (contentArea) {
                contentArea.innerHTML = components.loader('Retrying AI analysis…');
                this._renderTab(tab, contentArea).catch(() => {});
            }
        });
    }

    // ─── Compare ──────────────────────────────────────────────────────────────

    async _renderCompare() {
        this.root.innerHTML = `<div class="page-container">${components.loader('Loading comparison tool…')}</div>`;

        let docs = [];
        try {
            const data = await api.listDocuments();
            docs = data.documents || [];
        } catch { /* non-fatal */ }

        const { html, bindEvents } = views.compare(docs);
        this.root.innerHTML = `<div class="page-container">${html}</div>`;
        bindEvents(this);
    }

    // ─── Upload ───────────────────────────────────────────────────────────────

    async handleUpload(file) {
        if (!file) return;

        this.root.innerHTML = `
            <div class="page-container">
                ${components.loader(`Uploading ${components.escapeHtml(file.name)}… this may take a moment`)}
            </div>`;

        try {
            const doc = await api.uploadDocument(file);
            this._setCurrentDoc(doc.id);
            this.document = doc;
            this.cache.clear();
            components.toast(`"${doc.filename}" uploaded successfully!`, 'success');
            window.location.hash = '/workspace/summary';
        } catch (err) {
            components.toast(`Upload failed: ${err.message}`, 'error');
            await this._renderHome();
        }
    }

    // ─── Demo ─────────────────────────────────────────────────────────────────

    async handleDemo() {
        this.root.innerHTML = `<div class="page-container">${components.loader('Loading sample employment agreement…')}</div>`;

        try {
            const doc = await api.loadDemo();
            this._setCurrentDoc(doc.id);
            this.document = doc;
            this.cache.clear();
            components.toast('Sample agreement loaded!', 'success');
            window.location.hash = '/workspace/summary';
        } catch (err) {
            components.toast(`Could not load demo: ${err.message}`, 'error');
            await this._renderHome();
        }
    }

    // ─── Open existing doc ────────────────────────────────────────────────────

    openDocument(docId) {
        if (this.currentDocId !== docId) {
            this._setCurrentDoc(docId);
            this.document = null;
            this.cache.clear();
        }
        window.location.hash = '/workspace/summary';
    }

    // ─── Delete ───────────────────────────────────────────────────────────────

    async handleDelete(docId) {
        if (!confirm('Delete this document and all its analysis? This cannot be undone.')) return;

        try {
            await api.deleteDocument(docId);
            if (this.currentDocId === docId) this._clearCurrentDoc();
            components.toast('Document deleted.', 'info');
            await this._renderHome();
        } catch (err) {
            components.toast(`Delete failed: ${err.message}`, 'error');
        }
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    async _cached(key, fetcher) {
        if (this.cache.has(key)) return this.cache.get(key);
        const data = await fetcher();
        this.cache.set(key, data);
        return data;
    }

    _setCurrentDoc(id) {
        this.currentDocId = id;
        localStorage.setItem('legallens_current_doc', id);
    }

    _clearCurrentDoc() {
        this.currentDocId = null;
        this.document     = null;
        this.cache.clear();
        localStorage.removeItem('legallens_current_doc');
    }
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    window.app.init();
});

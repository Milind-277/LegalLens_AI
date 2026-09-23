/**
 * LegalLens AI — UI Components Library
 * Pure-JS component helpers; no framework dependency.
 */

export const components = {

    // ─── Toast Notifications ──────────────────────────────────────────────────

    toast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');

        const icon = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
        }[type] || '✓';

        toast.innerHTML = `
            <span style="margin-right:0.5rem;font-size:1rem">${icon}</span>
            <span style="flex:1">${this.escapeHtml(message)}</span>
            <button class="toast-close" aria-label="Close notification">×</button>
        `;

        toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
        container.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 5500);
    },

    // ─── Loaders ─────────────────────────────────────────────────────────────

    loader(text = 'Loading…') {
        return `
            <div class="loading-state" role="status" aria-label="${this.escapeHtml(text)}">
                <div class="spinner" aria-hidden="true"></div>
                <p class="loading-text">${this.escapeHtml(text)}</p>
            </div>
        `;
    },

    // ─── Badges ──────────────────────────────────────────────────────────────

    badge(text, type = 'neutral') {
        // Normalise type to a CSS class name
        const typeMap = {
            'HIGH': 'high', 'REVIEW': 'review', 'MEDIUM': 'medium', 'LOW': 'low',
            'added': 'added', 'removed': 'removed', 'changed': 'changed', 'unchanged': 'unchanged',
            'ai': 'ai', 'fallback': 'fallback', 'demo': 'demo',
        };
        const cls = typeMap[text] || typeMap[type] || 'neutral';
        return `<span class="badge badge-${cls}">${this.escapeHtml(text)}</span>`;
    },

    priorityBadge(priority) {
        return this.badge(priority || 'MEDIUM', priority || 'MEDIUM');
    },

    modeBadge(isFallback) {
        return isFallback
            ? `<span class="badge badge-fallback">Document Analysis</span>`
            : `<span class="badge badge-ai">✦ AI Enhanced</span>`;
    },

    // ─── Citation / Evidence Block ────────────────────────────────────────────

    citation(cit) {
        if (!cit || !cit.text) return '';

        let source = '';
        if (cit.page) source += `Page ${cit.page}`;
        if (cit.section) source += (source ? ' · ' : '') + `§ ${cit.section}`;

        return `
            <div class="evidence-box">
                <p>"${this.escapeHtml(cit.text)}"</p>
                ${source ? `<div class="citation-ref">📍 ${this.escapeHtml(source)}</div>` : ''}
            </div>
        `;
    },

    // ─── Fallback Notice Banner ───────────────────────────────────────────────

    fallbackNotice(retryFn = null) {
        const retryBtn = retryFn
            ? `<button class="btn btn-secondary btn-sm mt-2" id="retry-ai-btn">↺ Retry AI Analysis</button>`
            : '';
        return `
            <div class="fallback-notice" role="note">
                <svg class="fallback-notice-icon" aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 3h.01M12 2a10 10 0 100 20A10 10 0 0012 2z"/>
                </svg>
                <div class="fallback-notice-content">
                    <div class="fallback-notice-title">Document-Based Analysis Active</div>
                    <div>Live AI is temporarily unavailable (quota or configuration). Your document is fully preserved
                    and deterministic analysis is shown below. Results are based on keyword extraction from your document.
                    ${retryBtn}</div>
                </div>
            </div>
        `;
    },

    demoNotice() {
        return `
            <div class="demo-notice" role="note">
                <span style="font-size:1.25rem;flex-shrink:0">📄</span>
                <div>
                    <strong>Demo Document</strong> — This is a synthetic employment agreement created for demonstration purposes.
                    It is <em>not</em> a real legal document. Upload your own document to analyse it.
                </div>
            </div>
        `;
    },

    // ─── Empty State ──────────────────────────────────────────────────────────

    empty(title, description = '') {
        return `
            <div class="empty-state">
                <svg class="empty-state-icon" aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round"
                        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
                </svg>
                <h3>${this.escapeHtml(title)}</h3>
                ${description ? `<p>${this.escapeHtml(description)}</p>` : ''}
            </div>
        `;
    },

    // ─── XSS Protection ──────────────────────────────────────────────────────

    escapeHtml(unsafe) {
        if (unsafe == null) return '';
        return String(unsafe)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    // ─── Format helpers ───────────────────────────────────────────────────────

    formatFileSize(bytes) {
        if (!bytes) return '—';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    },

    formatDate(isoString) {
        if (!isoString) return '—';
        try {
            return new Date(isoString).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric',
            });
        } catch {
            return isoString;
        }
    },

    docTypeIcon(fileType) {
        const map = { pdf: 'doc-icon-pdf', docx: 'doc-icon-docx', txt: 'doc-icon-txt' };
        const cls = map[fileType?.toLowerCase()] || 'doc-icon-txt';
        const label = (fileType || 'TXT').toUpperCase();
        return `<div class="doc-item-icon ${cls}" aria-hidden="true">${this.escapeHtml(label)}</div>`;
    },
};

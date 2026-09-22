/**
 * LegalLens AI - UI Components
 */

export const components = {
    /**
     * Shows a toast notification
     */
    toast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        toast.innerHTML = `
            <span>${this.escapeHtml(message)}</span>
            <button style="background:none;border:none;color:white;cursor:pointer;font-size:1.2rem;" aria-label="Close">&times;</button>
        `;
        
        toast.querySelector('button').addEventListener('click', () => toast.remove());
        
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 5000);
    },

    /**
     * Creates a loading spinner element
     */
    loader(text = 'Loading...') {
        return `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>${this.escapeHtml(text)}</p>
            </div>
        `;
    },

    /**
     * Creates a badge element
     */
    badge(text, type = 'medium') {
        const typeClass = `badge-${type.toLowerCase()}`;
        return `<span class="badge ${typeClass}">${this.escapeHtml(text)}</span>`;
    },

    /**
     * Formats a citation block
     */
    citation(cit) {
        if (!cit || !cit.text) return '';
        
        let source = '';
        if (cit.page) source += `Page ${cit.page}`;
        if (cit.section) source += (source ? ' | ' : '') + `Section: ${cit.section}`;
        
        return `
            <div class="evidence-box">
                <p>"${this.escapeHtml(cit.text)}"</p>
                ${source ? `<div class="citation-ref">Source: ${this.escapeHtml(source)}</div>` : ''}
            </div>
        `;
    },

    /**
     * Simple HTML escaper to prevent XSS in Vanilla JS
     */
    escapeHtml(unsafe) {
        if (unsafe == null) return '';
        return String(unsafe)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
};

/**
 * LegalLens AI - Application State and Routing
 */
import { api } from './api.js';
import { components } from './components.js';
import { views } from './views.js';

class App {
    constructor() {
        this.root = document.getElementById('app-root');
        this.currentDocId = localStorage.getItem('legallens_current_doc');
        this.document = null;
        this.cache = new Map();
        
        this.init();
    }

    async init() {
        // Setup disclaimer dismissal
        document.querySelector('.dismiss-banner')?.addEventListener('click', (e) => {
            e.target.closest('.legal-disclaimer-banner').style.display = 'none';
        });

        // Setup routing
        window.addEventListener('hashchange', () => this.handleRoute());
        
        // Initial load
        await this.handleRoute();
    }

    async handleRoute() {
        const hash = window.location.hash.slice(1) || '/';
        
        // Update nav active state
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${hash.split('/')[1] || '/'}`) {
                link.classList.add('active');
            }
        });

        // Show/hide workspace link based on active document
        const wsLink = document.getElementById('nav-workspace');
        if (wsLink) {
            wsLink.style.display = this.currentDocId ? 'inline-block' : 'none';
        }

        try {
            if (hash === '/') {
                await this.renderHome();
            } else if (hash === '/workspace') {
                if (!this.currentDocId) {
                    window.location.hash = '/';
                    return;
                }
                await this.renderWorkspace('summary');
            } else if (hash.startsWith('/workspace/')) {
                if (!this.currentDocId) {
                    window.location.hash = '/';
                    return;
                }
                const tab = hash.split('/')[2];
                await this.renderWorkspace(tab);
            } else if (hash === '/compare') {
                await this.renderCompare();
            } else {
                this.root.innerHTML = '<h2>404 - Not Found</h2>';
            }
        } catch (error) {
            components.toast(error.message, 'error');
            this.root.innerHTML = `<div class="card card-body text-center" style="color:var(--danger)">Error loading view: ${components.escapeHtml(error.message)}</div>`;
        }
    }

    // --- Data Fetching ---

    async loadCurrentDocument() {
        if (!this.currentDocId) return false;
        
        try {
            if (!this.document || this.document.id !== this.currentDocId) {
                this.document = await api.getDocument(this.currentDocId);
                // Clear cache when document changes
                this.cache.clear(); 
            }
            return true;
        } catch (error) {
            console.error("Failed to load document", error);
            this.currentDocId = null;
            this.document = null;
            localStorage.removeItem('legallens_current_doc');
            return false;
        }
    }

    async fetchWithCache(key, fetcher) {
        if (this.cache.has(key)) return this.cache.get(key);
        const data = await fetcher();
        this.cache.set(key, data);
        return data;
    }

    // --- Renderers ---

    async renderHome() {
        const { html, bindEvents } = views.home();
        this.root.innerHTML = html;
        bindEvents(this);
    }

    async renderWorkspace(tab) {
        const loaded = await this.loadCurrentDocument();
        if (!loaded) {
            window.location.hash = '/';
            return;
        }

        // Render skeleton
        this.root.innerHTML = views.workspaceLayout(this.document, tab);
        
        // Render content
        const contentArea = document.getElementById('workspace-content');
        contentArea.innerHTML = components.loader(`Analyzing document for ${tab}...`);
        
        try {
            let html = '';
            let bindEvents = null;
            
            switch (tab) {
                case 'summary':
                    const summary = await this.fetchWithCache('summary', () => api.getSummary(this.currentDocId));
                    html = views.summary(summary);
                    break;
                case 'clauses':
                    const clausesData = await this.fetchWithCache('clauses', () => api.getClauses(this.currentDocId));
                    html = views.clauses(clausesData.clauses);
                    break;
                case 'risks':
                    const risksData = await this.fetchWithCache('risks', () => api.getRisks(this.currentDocId));
                    html = views.risks(risksData.review_flags, risksData.obligations);
                    break;
                case 'qa':
                    const qaView = views.qa(this.currentDocId);
                    html = qaView.html;
                    bindEvents = qaView.bindEvents;
                    break;
                case 'checklist':
                    const checklistData = await this.fetchWithCache('checklist', () => api.getChecklist(this.currentDocId));
                    html = views.checklist(checklistData.checklist);
                    break;
                case 'lawyer':
                    const lawyerData = await this.fetchWithCache('lawyer', () => api.getLawyerQuestions(this.currentDocId));
                    html = views.lawyer(lawyerData.questions);
                    break;
                default:
                    html = `<p>Unknown tab.</p>`;
            }
            
            contentArea.innerHTML = html;
            if (bindEvents) bindEvents(this);
            
        } catch (error) {
            contentArea.innerHTML = `<div class="card card-body text-center"><p style="color:var(--danger)">Analysis failed: ${components.escapeHtml(error.message)}</p></div>`;
        }
    }

    async renderCompare() {
        this.root.innerHTML = components.loader('Loading comparison tool...');
        try {
            const data = await api.listDocuments();
            const { html, bindEvents } = views.compare(data.documents);
            this.root.innerHTML = html;
            bindEvents(this);
        } catch (error) {
            this.root.innerHTML = `<p>Error loading comparison tool.</p>`;
        }
    }

    // --- Actions ---

    async handleUpload(file) {
        if (!file) return;
        
        this.root.innerHTML = components.loader('Uploading and processing document (this may take a moment)...');
        
        try {
            const doc = await api.uploadDocument(file);
            this.currentDocId = doc.id;
            localStorage.setItem('legallens_current_doc', doc.id);
            components.toast('Document uploaded successfully!');
            window.location.hash = '/workspace/summary';
        } catch (error) {
            components.toast(`Upload failed: ${error.message}`, 'error');
            await this.renderHome(); // go back
        }
    }
}

// Start app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});

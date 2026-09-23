/**
 * LegalLens AI — API Client
 * All backend communication goes through this module.
 */

class ApiClient {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        const headers = {
            'Accept': 'application/json',
            ...options.headers,
        };

        if (options.body && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, { ...options, headers });
            const data = await response.json();

            if (!response.ok || !data.success) {
                const errorMessage = data.error?.message || `Request failed (${response.status})`;
                throw new Error(errorMessage);
            }

            const result = data.data;
            // Attach metadata for analysis_mode / ai_available flags
            if (result && typeof result === 'object' && data.metadata) {
                result._metadata = data.metadata;
            }
            return result;
        } catch (error) {
            console.error('API Error:', endpoint, error.message);
            throw error;
        }
    }

    // ─── Documents ───────────────────────────────────────────────────────────

    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/documents/upload', { method: 'POST', body: formData });
    }

    async loadDemo() {
        return this.request('/documents/demo', { method: 'POST' });
    }

    async listDocuments() {
        return this.request('/documents');
    }

    async getDocument(docId) {
        return this.request(`/documents/${docId}`);
    }

    async deleteDocument(docId) {
        return this.request(`/documents/${docId}`, { method: 'DELETE' });
    }

    // ─── Analysis ────────────────────────────────────────────────────────────

    async getSummary(docId) {
        return this.request(`/documents/${docId}/summary`);
    }

    async getClauses(docId) {
        return this.request(`/documents/${docId}/clauses`);
    }

    async getRisks(docId) {
        return this.request(`/documents/${docId}/risks`);
    }

    async getChecklist(docId) {
        return this.request(`/documents/${docId}/checklist`);
    }

    async getLawyerQuestions(docId) {
        return this.request(`/documents/${docId}/lawyer-questions`);
    }

    // ─── Q&A ─────────────────────────────────────────────────────────────────

    async askQuestion(docId, question) {
        return this.request(`/documents/${docId}/ask`, {
            method: 'POST',
            body: { question },
        });
    }

    // ─── Comparison ──────────────────────────────────────────────────────────

    async compareDocuments(docAId, docBId) {
        return this.request('/documents/compare', {
            method: 'POST',
            body: { document_a_id: docAId, document_b_id: docBId },
        });
    }

    // ─── Status ──────────────────────────────────────────────────────────────

    async getStatus() {
        return this.request('/status');
    }
}

export const api = new ApiClient();

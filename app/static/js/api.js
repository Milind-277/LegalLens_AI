/**
 * LegalLens AI - API Client
 */

class ApiClient {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const headers = {
            'Accept': 'application/json',
            ...options.headers
        };

        if (options.body && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, { ...options, headers });
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                const errorMessage = data.error?.message || `HTTP Error ${response.status}`;
                throw new Error(errorMessage);
            }
            
            return data.data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/documents/upload', {
            method: 'POST',
            body: formData
        });
    }

    async getDocument(docId) {
        return this.request(`/documents/${docId}`);
    }

    async listDocuments() {
        return this.request('/documents');
    }

    async deleteDocument(docId) {
        return this.request(`/documents/${docId}`, { method: 'DELETE' });
    }

    async getSummary(docId) {
        return this.request(`/documents/${docId}/summary`);
    }

    async getClauses(docId) {
        return this.request(`/documents/${docId}/clauses`);
    }

    async getRisks(docId) {
        return this.request(`/documents/${docId}/risks`);
    }

    async askQuestion(docId, question) {
        return this.request(`/documents/${docId}/ask`, {
            method: 'POST',
            body: { question }
        });
    }

    async getChecklist(docId) {
        return this.request(`/documents/${docId}/checklist`);
    }

    async getLawyerQuestions(docId) {
        return this.request(`/documents/${docId}/lawyer-questions`);
    }

    async compareDocuments(docAId, docBId) {
        return this.request('/documents/compare', {
            method: 'POST',
            body: { document_a_id: docAId, document_b_id: docBId }
        });
    }
}

export const api = new ApiClient();

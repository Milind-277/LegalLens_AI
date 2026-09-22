/**
 * LegalLens AI - View renderers
 */
import { api } from './api.js';
import { components } from './components.js';

const e = components.escapeHtml;

export const views = {
    // --- Home View ---
    home() {
        return {
            html: `
                <div style="max-width: 800px; margin: 0 auto;">
                    <div class="text-center mb-4">
                        <h1 style="font-size: 2.5rem; color: var(--primary);">Understand Your Legal Documents</h1>
                        <p style="font-size: 1.25rem; color: var(--text-muted);">
                            Upload a contract, agreement, or policy to get plain-language summaries, 
                            identify key obligations, and find potential risks.
                        </p>
                    </div>
                    
                    <div class="card card-body">
                        <h2 class="mb-2">Upload Document</h2>
                        <p class="mb-4 text-muted">Supported formats: PDF, DOCX, TXT. Max size: 10MB.</p>
                        
                        <div class="upload-area" id="drop-zone" tabindex="0" role="button" aria-label="Upload document">
                            <svg class="upload-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                            </svg>
                            <h3 style="margin-bottom: var(--spacing-xs)">Drag & Drop your file here</h3>
                            <p class="text-muted" style="margin-bottom: var(--spacing-md)">or click to browse</p>
                            <input type="file" id="file-input" class="hidden" accept=".pdf,.docx,.txt" aria-hidden="true">
                            <button class="btn btn-secondary">Select File</button>
                        </div>
                    </div>
                </div>
            `,
            bindEvents(app) {
                const dropZone = document.getElementById('drop-zone');
                const fileInput = document.getElementById('file-input');
                
                dropZone.addEventListener('click', () => fileInput.click());
                dropZone.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') fileInput.click();
                });
                
                dropZone.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                });
                
                dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
                
                dropZone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                    if (e.dataTransfer.files.length) {
                        app.handleUpload(e.dataTransfer.files[0]);
                    }
                });
                
                fileInput.addEventListener('change', () => {
                    if (fileInput.files.length) {
                        app.handleUpload(fileInput.files[0]);
                    }
                });
            }
        };
    },

    // --- Workspace Layout ---
    workspaceLayout(doc, currentTab) {
        const tabs = [
            { id: 'summary', label: 'Summary' },
            { id: 'clauses', label: 'Key Clauses' },
            { id: 'risks', label: 'Review & Obligations' },
            { id: 'qa', label: 'Ask Document' },
            { id: 'checklist', label: 'Action Checklist' },
            { id: 'lawyer', label: 'Lawyer Questions' }
        ];

        let navHtml = '';
        for (const tab of tabs) {
            const active = tab.id === currentTab ? 'active' : '';
            navHtml += `<a href="#/workspace/${tab.id}" class="sidebar-link ${active}">${e(tab.label)}</a>`;
        }

        return `
            <div class="flex-between mb-4">
                <div>
                    <h2>${e(doc.filename)}</h2>
                    <p class="text-muted text-sm">
                        Analyzed on ${new Date(doc.uploaded_at).toLocaleDateString()} | 
                        ${e(doc.metadata.detected_type)}
                    </p>
                </div>
                <button class="btn btn-secondary" onclick="localStorage.removeItem('legallens_current_doc'); window.location.hash='/';">
                    Analyze New Document
                </button>
            </div>
            
            <div class="dashboard-grid">
                <nav class="sidebar-nav" aria-label="Workspace Navigation">
                    ${navHtml}
                </nav>
                <div id="workspace-content" role="region" aria-live="polite"></div>
            </div>
        `;
    },

    // --- Summary View ---
    summary(data) {
        return `
            <div class="card mb-4">
                <div class="card-header"><h3 style="margin:0">Quick Summary</h3></div>
                <div class="card-body">
                    <p style="font-size: 1.125rem">${e(data.quick_summary)}</p>
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-header"><h3 style="margin:0">Detailed Overview</h3></div>
                <div class="card-body">
                    <p style="white-space: pre-wrap">${e(data.detailed_summary)}</p>
                </div>
            </div>
            
            <div class="dashboard-grid" style="grid-template-columns: 1fr 1fr; gap: var(--spacing-md)">
                <div class="card">
                    <div class="card-header"><h3 style="margin:0">Key Points</h3></div>
                    <div class="card-body">
                        <ul style="padding-left: 1.5rem">
                            ${data.key_points.map(pt => `<li>${e(pt)}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header"><h3 style="margin:0">Parties</h3></div>
                    <div class="card-body">
                        <ul style="padding-left: 1.5rem">
                            ${data.parties.map(pt => `<li>${e(pt)}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    },

    // --- Clauses View ---
    clauses(clauses) {
        if (!clauses.length) return `<div class="card card-body">No important clauses detected.</div>`;
        
        let html = '';
        for (const c of clauses) {
            html += `
                <div class="card mb-4">
                    <div class="card-header flex-between">
                        <h3 style="margin:0">${e(c.title || c.category)}</h3>
                        ${components.badge(c.category, 'info')}
                    </div>
                    <div class="card-body">
                        <p class="mb-2"><strong>What it means:</strong> ${e(c.explanation)}</p>
                        ${components.citation(c.citation)}
                    </div>
                </div>
            `;
        }
        return html;
    },

    // --- Risks & Obligations View ---
    risks(flags, obligations) {
        let html = '';
        
        html += '<h2 class="mb-2">Document Review Flags</h2>';
        html += '<p class="text-muted mb-4">Areas that may require your attention or professional review. These are not legal conclusions.</p>';
        
        if (flags && flags.length) {
            for (const f of flags) {
                html += `
                    <div class="card mb-4" style="border-left: 4px solid var(--warning)">
                        <div class="card-header flex-between">
                            <h3 style="margin:0">${e(f.title)}</h3>
                            ${components.badge(f.review_priority, f.review_priority)}
                        </div>
                        <div class="card-body">
                            <p class="mb-2"><strong>Concern:</strong> ${e(f.explanation)}</p>
                            ${f.suggested_action ? `<p class="mb-2 text-muted"><strong>Suggestion:</strong> ${e(f.suggested_action)}</p>` : ''}
                            ${components.citation(f.citation)}
                        </div>
                    </div>
                `;
            }
        } else {
            html += `<div class="card card-body mb-4">No significant review flags detected.</div>`;
        }
        
        html += '<h2 class="mb-2 mt-4">Explicit Obligations</h2>';
        if (obligations && obligations.length) {
            for (const o of obligations) {
                html += `
                    <div class="card mb-4" style="border-left: 4px solid var(--primary)">
                        <div class="card-body">
                            <div class="flex-between mb-2">
                                <strong>${e(o.actor)}</strong> must:
                                ${o.deadline ? components.badge(`Due: ${o.deadline}`, 'info') : ''}
                            </div>
                            <p class="mb-2">${e(o.obligation)}</p>
                            ${components.citation(o.citation)}
                        </div>
                    </div>
                `;
            }
        } else {
            html += `<div class="card card-body mb-4">No explicit obligations detected.</div>`;
        }
        
        return html;
    },

    // --- Q&A View ---
    qa(docId) {
        return {
            html: `
                <div class="card" style="height: 100%; display: flex; flex-direction: column;">
                    <div class="card-header">
                        <h3 style="margin:0">Ask Questions</h3>
                        <p class="text-muted text-sm mt-1">Get answers grounded directly in your uploaded document.</p>
                    </div>
                    <div class="card-body" style="flex: 1; display: flex; flex-direction: column;">
                        <div id="chat-history" class="chat-container" style="flex: 1; min-height: 300px;">
                            <div class="message message-ai">
                                Hello! I've analyzed your document. What would you like to know?
                            </div>
                        </div>
                        
                        <form id="qa-form" style="display: flex; gap: var(--spacing-sm); margin-top: var(--spacing-md)">
                            <input type="text" id="qa-input" class="form-control" placeholder="E.g., What is the notice period?" required autocomplete="off">
                            <button type="submit" class="btn btn-primary" id="qa-submit">Ask</button>
                        </form>
                    </div>
                </div>
            `,
            bindEvents(app) {
                const form = document.getElementById('qa-form');
                const input = document.getElementById('qa-input');
                const submit = document.getElementById('qa-submit');
                const history = document.getElementById('chat-history');
                
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const question = input.value.trim();
                    if (!question) return;
                    
                    // Add user message
                    history.innerHTML += `<div class="message message-user">${components.escapeHtml(question)}</div>`;
                    input.value = '';
                    input.disabled = true;
                    submit.disabled = true;
                    
                    // Add loading indicator
                    const loaderId = 'loader-' + Date.now();
                    history.innerHTML += `<div id="${loaderId}" class="message message-ai" style="opacity:0.7">Searching document...</div>`;
                    history.scrollTop = history.scrollHeight;
                    
                    try {
                        const res = await api.askQuestion(docId, question);
                        document.getElementById(loaderId).remove();
                        
                        let ansHtml = `<div class="message message-ai">`;
                        ansHtml += `<p>${components.escapeHtml(res.answer)}</p>`;
                        
                        // Disclaimer
                        if (res.disclaimer) {
                            ansHtml += `<p class="mt-2 text-sm" style="color:var(--warning)"><strong>Note:</strong> ${components.escapeHtml(res.disclaimer)}</p>`;
                        }
                        
                        // Citations
                        if (res.citations && res.citations.length) {
                            ansHtml += `<div class="mt-2" style="border-top:1px solid var(--border-light); padding-top:var(--spacing-sm)">
                                <strong class="text-sm">Source Evidence:</strong>`;
                            for (const c of res.citations) {
                                ansHtml += components.citation(c);
                            }
                            ansHtml += `</div>`;
                        } else if (res.grounding_status === 'not_found') {
                            ansHtml += `<div class="mt-2 text-sm text-muted">No specific evidence found in document.</div>`;
                        }
                        
                        ansHtml += `</div>`;
                        history.innerHTML += ansHtml;
                        
                    } catch (error) {
                        document.getElementById(loaderId).remove();
                        history.innerHTML += `<div class="message message-ai" style="color:var(--danger)">Error: ${components.escapeHtml(error.message)}</div>`;
                    } finally {
                        input.disabled = false;
                        submit.disabled = false;
                        input.focus();
                        history.scrollTop = history.scrollHeight;
                    }
                });
            }
        };
    },

    // --- Checklist View ---
    checklist(items) {
        if (!items || !items.length) return `<div class="card card-body">No clear action items identified.</div>`;
        
        let html = '<div class="card"><div class="card-body" style="padding:0">';
        html += '<ul style="list-style:none; padding:0; margin:0">';
        
        for (const item of items) {
            html += `
                <li style="border-bottom: 1px solid var(--border-light); padding: var(--spacing-md) var(--spacing-lg);">
                    <label style="display:flex; gap: var(--spacing-md); align-items: flex-start; cursor: pointer;">
                        <input type="checkbox" style="margin-top: 5px; width: 1.25rem; height: 1.25rem;">
                        <div style="flex: 1">
                            <div class="flex-between mb-1">
                                <strong>${e(item.action)}</strong>
                                ${components.badge(item.priority, item.priority)}
                            </div>
                            <div class="text-muted text-sm flex-between">
                                <span>Responsibility: ${e(item.responsible_party || 'Unspecified')}</span>
                                ${item.deadline ? `<span>Due: ${e(item.deadline)}</span>` : ''}
                            </div>
                        </div>
                    </label>
                </li>
            `;
        }
        
        html += '</ul></div></div>';
        return html;
    },

    // --- Lawyer Questions View ---
    lawyer(questions) {
        if (!questions || !questions.length) return `<div class="card card-body">No specific questions identified.</div>`;
        
        let html = `<p class="mb-4">Consider asking a qualified legal professional the following questions based on this document's content.</p>`;
        
        for (const q of questions) {
            html += `
                <div class="card mb-4" style="border-left: 4px solid var(--accent)">
                    <div class="card-body">
                        <h4 class="mb-2" style="font-size:1.125rem; color: var(--text-main)">"${e(q.question)}"</h4>
                        <p class="text-muted text-sm mb-2"><strong>Context:</strong> ${e(q.context)}</p>
                        ${q.related_clause ? `<p class="text-muted text-sm"><strong>Refers to:</strong> ${e(q.related_clause)}</p>` : ''}
                    </div>
                </div>
            `;
        }
        return html;
    },

    // --- Compare View ---
    compare(documents) {
        return {
            html: `
                <div class="card mb-4">
                    <div class="card-header"><h2>Compare Documents</h2></div>
                    <div class="card-body">
                        <form id="compare-form" class="dashboard-grid" style="grid-template-columns: 1fr 1fr; gap: var(--spacing-md)">
                            <div class="form-group">
                                <label class="form-label" for="doc-a">Document A</label>
                                <select id="doc-a" class="form-control" required>
                                    <option value="">Select first document...</option>
                                    ${documents.map(d => `<option value="${e(d.id)}">${e(d.filename)}</option>`).join('')}
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="doc-b">Document B</label>
                                <select id="doc-b" class="form-control" required>
                                    <option value="">Select second document...</option>
                                    ${documents.map(d => `<option value="${e(d.id)}">${e(d.filename)}</option>`).join('')}
                                </select>
                            </div>
                            <div style="grid-column: 1 / -1; text-align: center">
                                <button type="submit" class="btn btn-primary" id="compare-btn">Run Comparison</button>
                            </div>
                        </form>
                    </div>
                </div>
                <div id="compare-result" aria-live="polite"></div>
            `,
            bindEvents(app) {
                const form = document.getElementById('compare-form');
                const resultArea = document.getElementById('compare-result');
                const btn = document.getElementById('compare-btn');
                
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const docAId = document.getElementById('doc-a').value;
                    const docBId = document.getElementById('doc-b').value;
                    
                    if (docAId === docBId) {
                        components.toast('Please select two different documents to compare', 'error');
                        return;
                    }
                    
                    btn.disabled = true;
                    resultArea.innerHTML = components.loader('Analyzing differences... This may take up to a minute.');
                    
                    try {
                        const res = await api.compareDocuments(docAId, docBId);
                        
                        let resHtml = `
                            <div class="card mb-4">
                                <div class="card-body">
                                    <h3 class="mb-2">Summary of Differences</h3>
                                    <p>${components.escapeHtml(res.summary)}</p>
                                    <ul class="mt-2" style="padding-left:1.5rem">
                                        ${res.key_differences.map(d => `<li>${components.escapeHtml(d)}</li>`).join('')}
                                    </ul>
                                </div>
                            </div>
                        `;
                        
                        for (const item of res.items) {
                            let badgeType = 'info';
                            if (item.status === 'added') badgeType = 'success';
                            if (item.status === 'removed') badgeType = 'danger';
                            if (item.status === 'changed') badgeType = 'warning';
                            
                            resHtml += `
                                <div class="card mb-4">
                                    <div class="card-header flex-between">
                                        <h3 style="margin:0">${components.escapeHtml(item.category)}</h3>
                                        ${components.badge(item.status.toUpperCase(), badgeType)}
                                    </div>
                                    <div class="card-body">
                                        <p class="mb-4"><strong>Analysis:</strong> ${components.escapeHtml(item.explanation)}</p>
                                        
                                        <div class="dashboard-grid" style="grid-template-columns: 1fr 1fr; gap: var(--spacing-md)">
                                            <div style="background:var(--bg-alt); padding:var(--spacing-md); border-radius:var(--radius-md);">
                                                <h4 class="text-sm text-muted mb-2">Document A</h4>
                                                <p class="text-sm" style="white-space:pre-wrap">${components.escapeHtml(item.document_a) || '<em>None</em>'}</p>
                                            </div>
                                            <div style="background:var(--bg-alt); padding:var(--spacing-md); border-radius:var(--radius-md);">
                                                <h4 class="text-sm text-muted mb-2">Document B</h4>
                                                <p class="text-sm" style="white-space:pre-wrap">${components.escapeHtml(item.document_b) || '<em>None</em>'}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }
                        
                        resultArea.innerHTML = resHtml;
                    } catch (error) {
                        resultArea.innerHTML = `<div class="card card-body text-center"><p style="color:var(--danger)">Comparison failed: ${components.escapeHtml(error.message)}</p></div>`;
                    } finally {
                        btn.disabled = false;
                    }
                });
            }
        };
    }
};

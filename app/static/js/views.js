/**
 * LegalLens AI — View Renderers
 * Each view returns HTML string(s) and/or a bindEvents function.
 */
import { api } from './api.js';
import { components } from './components.js';

const e = (s) => components.escapeHtml(s);

// ─── Workspace Sidebar Tabs ────────────────────────────────────────────────────
const WORKSPACE_TABS = [
    { id: 'summary',   label: 'Summary',           icon: '📋' },
    { id: 'clauses',   label: 'Key Clauses',        icon: '📑' },
    { id: 'risks',     label: 'Review & Obligations', icon: '⚠️' },
    { id: 'qa',        label: 'Ask Document',       icon: '💬' },
    { id: 'checklist', label: 'Action Checklist',   icon: '✅' },
    { id: 'lawyer',    label: 'Lawyer Questions',   icon: '⚖️' },
];

export const views = {

    // ═══════════════════════════════════════════════════════════════════════════
    //  HOME PAGE
    // ═══════════════════════════════════════════════════════════════════════════
    home(documents = []) {
        const docListHtml = documents.length > 0
            ? documents.map(doc => `
                <div class="doc-item" role="button" tabindex="0"
                     data-doc-id="${e(doc.id)}"
                     aria-label="Open ${e(doc.filename)}">
                    ${components.docTypeIcon(doc.file_type)}
                    <div class="doc-item-info">
                        <div class="doc-item-name">${e(doc.filename)}</div>
                        <div class="doc-item-meta">
                            <span>${e(doc.metadata?.detected_type || 'Document')}</span>
                            <span>${components.formatFileSize(doc.file_size)}</span>
                            <span>${components.formatDate(doc.uploaded_at)}</span>
                        </div>
                    </div>
                    <div class="doc-item-actions">
                        <button class="btn btn-primary btn-sm" data-open-doc="${e(doc.id)}"
                                aria-label="Analyse ${e(doc.filename)}">
                            Open
                        </button>
                        <button class="btn btn-ghost btn-sm btn-icon" data-delete-doc="${e(doc.id)}"
                                aria-label="Delete ${e(doc.filename)}" title="Delete">
                            🗑
                        </button>
                    </div>
                </div>
            `).join('')
            : `<div class="empty-state" style="padding: var(--space-8)">
                   <p class="text-muted text-sm">No documents yet. Upload one above or try the demo.</p>
               </div>`;

        return {
            html: `
                <div class="home-hero">
                    <div class="home-hero-eyebrow">
                        <span>⚖</span> Legal Document Intelligence
                    </div>
                    <h1>Understand Your <span class="highlight">Legal Documents</span></h1>
                    <p class="home-hero-desc">
                        Upload a contract, agreement, or policy to get plain-language summaries,
                        identify key obligations, spot review points, and prepare questions for your attorney.
                    </p>

                    <div class="feature-pills" aria-label="Feature highlights">
                        <span class="feature-pill"><span class="feature-pill-icon">📋</span>Plain-Language Summary</span>
                        <span class="feature-pill"><span class="feature-pill-icon">📑</span>Clause Extraction</span>
                        <span class="feature-pill"><span class="feature-pill-icon">⚠️</span>Review Flags</span>
                        <span class="feature-pill"><span class="feature-pill-icon">💬</span>Document Q&amp;A</span>
                        <span class="feature-pill"><span class="feature-pill-icon">✅</span>Action Checklist</span>
                        <span class="feature-pill"><span class="feature-pill-icon">⚖️</span>Lawyer Questions</span>
                    </div>
                </div>

                <!-- Upload Card -->
                <div class="card mb-6">
                    <div class="card-header">
                        <h2 style="margin:0;font-size:var(--text-lg)">Upload a Document</h2>
                        <span class="text-muted text-sm">PDF · DOCX · TXT · Max 10 MB</span>
                    </div>
                    <div class="card-body">
                        <div class="upload-area" id="drop-zone" tabindex="0" role="button"
                             aria-label="Upload legal document — click or drag a file here">
                            <svg class="upload-icon" width="52" height="52" viewBox="0 0 24 24"
                                 fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                                <path stroke-linecap="round" stroke-linejoin="round"
                                    d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 5.75 5.75 0 011.344 11.095"/>
                            </svg>
                            <h3 class="upload-title">Drag &amp; drop your file here</h3>
                            <p class="upload-subtitle">or click to browse your computer</p>
                            <input type="file" id="file-input" class="hidden"
                                   accept=".pdf,.docx,.txt" aria-label="Choose file to upload">
                            <button class="btn btn-primary" id="select-file-btn" type="button">
                                Choose File
                            </button>
                            <div class="upload-formats" aria-label="Supported file formats">
                                <span class="format-badge">PDF</span>
                                <span class="format-badge">DOCX</span>
                                <span class="format-badge">TXT</span>
                            </div>
                        </div>

                        <div class="text-center mt-4">
                            <span class="text-muted text-sm" style="margin:0 var(--space-4)">— or —</span>
                            <button class="btn btn-secondary" id="demo-btn" type="button">
                                📄 Try Sample Employment Agreement
                            </button>
                            <p class="text-xs text-muted mt-2">
                                Loads a synthetic demo document so you can explore all features without uploading.
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Recent Documents -->
                <div class="card">
                    <div class="card-header">
                        <h2 style="margin:0;font-size:var(--text-lg)">Your Documents</h2>
                        ${documents.length > 0 ? `<span class="badge badge-neutral">${documents.length}</span>` : ''}
                    </div>
                    <div id="doc-list">
                        ${docListHtml}
                    </div>
                </div>
            `,

            bindEvents(app) {
                const dropZone  = document.getElementById('drop-zone');
                const fileInput = document.getElementById('file-input');
                const selectBtn = document.getElementById('select-file-btn');
                const demoBtn   = document.getElementById('demo-btn');

                // Open file picker
                selectBtn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    fileInput.click();
                });

                // Click on drop zone (but not a button)
                dropZone.addEventListener('click', (ev) => {
                    if (ev.target.closest('button, input')) return;
                    fileInput.click();
                });

                dropZone.addEventListener('keydown', (ev) => {
                    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); fileInput.click(); }
                });

                // Drag & drop
                dropZone.addEventListener('dragover', (ev) => {
                    ev.preventDefault();
                    dropZone.classList.add('dragover');
                });
                dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
                dropZone.addEventListener('drop', (ev) => {
                    ev.preventDefault();
                    dropZone.classList.remove('dragover');
                    if (ev.dataTransfer.files.length) app.handleUpload(ev.dataTransfer.files[0]);
                });

                fileInput.addEventListener('change', () => {
                    if (fileInput.files.length) app.handleUpload(fileInput.files[0]);
                });

                // Demo button
                demoBtn.addEventListener('click', () => app.handleDemo());

                // Document list: open / delete
                document.getElementById('doc-list').addEventListener('click', (ev) => {
                    const openBtn = ev.target.closest('[data-open-doc]');
                    if (openBtn) {
                        app.openDocument(openBtn.dataset.openDoc);
                        return;
                    }
                    const delBtn = ev.target.closest('[data-delete-doc]');
                    if (delBtn) app.handleDelete(delBtn.dataset.deleteDoc);
                });

                // Also allow clicking the entire doc-item row to open
                document.querySelectorAll('.doc-item[data-doc-id]').forEach(item => {
                    item.addEventListener('keydown', (ev) => {
                        if (ev.key === 'Enter') app.openDocument(item.dataset.docId);
                    });
                });
            },
        };
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  WORKSPACE SHELL (sidebar + content area)
    // ═══════════════════════════════════════════════════════════════════════════
    workspaceShell(doc, currentTab) {
        const isDemo = doc.filename?.includes('DEMO');
        const navLinks = WORKSPACE_TABS.map(tab => `
            <a href="#/workspace/${tab.id}"
               class="sidebar-link ${tab.id === currentTab ? 'active' : ''}"
               aria-current="${tab.id === currentTab ? 'page' : 'false'}"
               id="tab-link-${tab.id}">
                <span aria-hidden="true">${tab.icon}</span>
                ${e(tab.label)}
            </a>
        `).join('');

        return `
            <div class="workspace-topbar">
                <div class="workspace-title-area">
                    <h1 class="workspace-doc-name">
                        ${e(doc.filename)}
                        ${isDemo ? components.badge('DEMO', 'demo') : ''}
                    </h1>
                    <div class="workspace-doc-meta">
                        <span class="meta-item">📁 ${e(doc.metadata?.detected_type || 'Document')}</span>
                        <span class="meta-item">📏 ${components.formatFileSize(doc.file_size)}</span>
                        <span class="meta-item">📅 ${components.formatDate(doc.uploaded_at)}</span>
                        ${doc.metadata?.page_count ? `<span class="meta-item">📄 ${doc.metadata.page_count} pages</span>` : ''}
                        ${doc.metadata?.word_count ? `<span class="meta-item">📝 ~${doc.metadata.word_count.toLocaleString()} words</span>` : ''}
                    </div>
                </div>
                <div class="flex gap-2">
                    <button class="btn btn-secondary" id="btn-new-doc" aria-label="Analyse a new document">
                        + New Document
                    </button>
                </div>
            </div>

            <div class="workspace-shell">
                <!-- Sidebar Navigation -->
                <aside class="workspace-sidebar" aria-label="Workspace navigation">
                    <div class="sidebar-card">
                        <div class="sidebar-header">
                            <div class="sidebar-doc-name" title="${e(doc.filename)}">${e(doc.filename)}</div>
                            <div class="sidebar-doc-meta">${e(doc.metadata?.detected_type || 'Document')}</div>
                        </div>
                        <nav class="sidebar-nav" aria-label="Document analysis sections">
                            ${navLinks}
                        </nav>
                        <div class="sidebar-footer">
                            <button class="btn btn-ghost btn-sm w-full" id="btn-delete-doc"
                                    aria-label="Delete this document" style="color:var(--danger)">
                                🗑 Delete Document
                            </button>
                        </div>
                    </div>
                </aside>

                <!-- Main Content Area -->
                <main id="workspace-content" role="main" aria-live="polite">
                    ${components.loader('Analysing…')}
                </main>
            </div>
        `;
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  SUMMARY
    // ═══════════════════════════════════════════════════════════════════════════
    summary(data, isFallback = false, isDemo = false) {
        const kp = data.key_points?.length
            ? data.key_points.map(pt => `<li class="mb-1 text-sm">• ${e(pt)}</li>`).join('')
            : '<li class="text-muted text-sm">No key points identified.</li>';

        const parties = data.parties?.length
            ? data.parties.map(p => `<li class="mb-1 text-sm">• ${e(p)}</li>`).join('')
            : '<li class="text-muted text-sm">No named parties extracted.</li>';

        const dates = data.key_dates?.length
            ? data.key_dates.map(d => `<li class="mb-1 text-sm">• ${e(d)}</li>`).join('')
            : '<li class="text-muted text-sm">No specific dates identified.</li>';

        return `
            ${isDemo ? components.demoNotice() : ''}
            ${isFallback ? components.fallbackNotice(true) : ''}

            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
                <h2 style="margin:0">Document Summary</h2>
                <div class="flex gap-2 items-center">
                    ${isFallback ? components.badge('Document Analysis', 'fallback') : components.badge('AI Enhanced', 'ai')}
                    ${data.document_type ? `<span class="badge badge-neutral">${e(data.document_type)}</span>` : ''}
                </div>
            </div>

            <!-- Executive / Quick Summary -->
            <div class="card mb-4">
                <div class="card-header">
                    <h3 style="margin:0">Quick Summary</h3>
                </div>
                <div class="card-body">
                    <p style="font-size:var(--text-lg);line-height:1.7;color:var(--text-primary)">
                        ${e(data.quick_summary || 'Summary not available.')}
                    </p>
                    ${data.effective_date ? `<p class="text-sm text-muted mt-3">📅 Effective Date: <strong>${e(data.effective_date)}</strong></p>` : ''}
                </div>
            </div>

            <!-- Key Facts Grid -->
            <div class="summary-grid mb-4">
                <div class="card">
                    <div class="card-header"><h3 style="margin:0">Key Points</h3></div>
                    <div class="card-body">
                        <ul style="list-style:none;padding:0;margin:0">${kp}</ul>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 style="margin:0">Parties Identified</h3></div>
                    <div class="card-body">
                        <ul style="list-style:none;padding:0;margin:0">${parties}</ul>
                    </div>
                </div>
            </div>

            <!-- Detailed Summary -->
            ${data.detailed_summary ? `
            <div class="card mb-4">
                <div class="card-header"><h3 style="margin:0">Detailed Overview</h3></div>
                <div class="card-body">
                    <p class="whitespace-pre text-sm" style="line-height:1.8;color:var(--text-secondary)">
                        ${e(data.detailed_summary)}
                    </p>
                </div>
            </div>` : ''}

            <!-- Important Dates -->
            <div class="card">
                <div class="card-header"><h3 style="margin:0">Important Dates</h3></div>
                <div class="card-body">
                    <ul style="list-style:none;padding:0;margin:0">${dates}</ul>
                </div>
            </div>
        `;
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  CLAUSES
    // ═══════════════════════════════════════════════════════════════════════════
    clauses(clauses, isFallback = false) {
        if (!clauses?.length) {
            return isFallback
                ? components.fallbackNotice() + components.empty('No Clauses Detected', 'Try uploading a longer document.')
                : components.empty('No Clauses Detected', 'The document may not contain identifiable clause structures.');
        }

        const items = clauses.map(c => `
            <div class="clause-card">
                <div class="clause-card-header">
                    <h3 class="clause-card-title">
                        ${e(c.title || c.category)}
                    </h3>
                    <div class="flex gap-2 items-center">
                        ${components.priorityBadge(c.review_priority)}
                        <span class="badge badge-neutral text-xs">${e(c.category)}</span>
                    </div>
                </div>
                <div class="clause-card-body">
                    <p class="text-sm mb-3" style="color:var(--text-secondary);line-height:1.7">${e(c.explanation)}</p>
                    ${components.citation(c.citation)}
                </div>
            </div>
        `).join('');

        return `
            ${isFallback ? components.fallbackNotice(true) : ''}
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
                <h2 style="margin:0">Key Clauses <span class="badge badge-neutral ml-2">${clauses.length}</span></h2>
                ${isFallback ? components.badge('Document Analysis', 'fallback') : components.badge('AI Enhanced', 'ai')}
            </div>
            <p class="text-sm text-muted mb-6">
                These are review indicators, not legal conclusions. Clauses marked <strong>HIGH</strong> or
                <strong>REVIEW</strong> may warrant professional attention.
            </p>
            ${items}
        `;
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  REVIEW FLAGS & OBLIGATIONS
    // ═══════════════════════════════════════════════════════════════════════════
    risks(flags, obligations, isFallback = false) {
        const flagsHtml = flags?.length
            ? flags.map(f => `
                <div class="clause-card review-flag-card">
                    <div class="clause-card-header">
                        <h3 class="clause-card-title">⚠ ${e(f.title)}</h3>
                        ${components.priorityBadge(f.review_priority)}
                    </div>
                    <div class="clause-card-body">
                        <p class="text-sm mb-3" style="line-height:1.7">${e(f.explanation)}</p>
                        ${f.suggested_action ? `
                        <p class="text-sm mb-3" style="color:var(--text-secondary)">
                            <strong>Suggested Action:</strong> ${e(f.suggested_action)}
                        </p>` : ''}
                        ${components.citation(f.citation)}
                    </div>
                </div>
            `).join('')
            : components.empty('No Review Flags', 'No significant concerns identified in this document.');

        const obligationsHtml = obligations?.length
            ? `<div class="card">
                <div class="card-header"><h3 style="margin:0">Obligations <span class="badge badge-neutral">${obligations.length}</span></h3></div>
                <div style="overflow-x:auto">
                    <table style="width:100%;border-collapse:collapse;font-size:var(--text-sm)">
                        <thead>
                            <tr style="background:var(--bg-alt);border-bottom:1px solid var(--border-subtle)">
                                <th style="padding:var(--space-3) var(--space-4);text-align:left;font-weight:600;color:var(--text-muted);font-size:var(--text-xs);text-transform:uppercase;letter-spacing:.05em">Party</th>
                                <th style="padding:var(--space-3) var(--space-4);text-align:left;font-weight:600;color:var(--text-muted);font-size:var(--text-xs);text-transform:uppercase;letter-spacing:.05em">Obligation</th>
                                <th style="padding:var(--space-3) var(--space-4);text-align:left;font-weight:600;color:var(--text-muted);font-size:var(--text-xs);text-transform:uppercase;letter-spacing:.05em">Deadline</th>
                                <th style="padding:var(--space-3) var(--space-4);text-align:left;font-weight:600;color:var(--text-muted);font-size:var(--text-xs);text-transform:uppercase;letter-spacing:.05em">Priority</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${obligations.map((o, i) => `
                                <tr style="${i % 2 === 0 ? '' : 'background:var(--bg-alt)'}; border-bottom:1px solid var(--border-subtle)">
                                    <td style="padding:var(--space-3) var(--space-4);font-weight:500">${e(o.actor)}</td>
                                    <td style="padding:var(--space-3) var(--space-4)">${e(o.obligation)}</td>
                                    <td style="padding:var(--space-3) var(--space-4);color:var(--text-muted)">${e(o.deadline || '—')}</td>
                                    <td style="padding:var(--space-3) var(--space-4)">${components.priorityBadge(o.review_priority)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
               </div>`
            : components.empty('No Obligations Found', 'No explicit obligations were identified.');

        return `
            ${isFallback ? components.fallbackNotice(true) : ''}

            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
                <h2 style="margin:0">Review & Obligations</h2>
                ${isFallback ? components.badge('Document Analysis', 'fallback') : components.badge('AI Enhanced', 'ai')}
            </div>

            <p class="text-sm text-muted mb-5">
                Review flags are <strong>document review indicators</strong> — not legal verdicts.
                Always consult a qualified attorney before acting on any findings.
            </p>

            <h3 class="mb-3" style="font-size:var(--text-base)">
                Review Flags ${flags?.length ? `<span class="badge badge-neutral">${flags.length}</span>` : ''}
            </h3>
            ${flagsHtml}

            <h3 class="mt-8 mb-4" style="font-size:var(--text-base)">Explicit Obligations</h3>
            ${obligationsHtml}
        `;
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  Q&A CHAT
    // ═══════════════════════════════════════════════════════════════════════════
    qa(docId) {
        const suggestedQs = [
            'What are my main obligations?',
            'When can this agreement be terminated?',
            'Are there automatic renewal terms?',
            'What should I clarify before signing?',
            'What is the notice period?',
        ];

        return {
            html: `
                <h2 class="mb-2">Ask Your Document</h2>
                <p class="text-sm text-muted mb-5">
                    Ask questions and get answers grounded directly in your uploaded document.
                    Answers will cite the specific section of the document that supports them.
                </p>

                <div class="card">
                    <div class="suggested-questions" aria-label="Suggested questions">
                        <span class="text-xs text-muted" style="align-self:center;flex-shrink:0">Try asking:</span>
                        ${suggestedQs.map(q => `<button class="suggested-q" data-q="${e(q)}">${e(q)}</button>`).join('')}
                    </div>

                    <div class="chat-shell">
                        <div id="chat-messages" class="chat-messages" aria-live="polite" aria-label="Conversation">
                            <div class="message message-ai">
                                <div class="message-bubble">
                                    👋 Hello! I've analysed your document. Ask me anything about it —
                                    I'll provide answers grounded in the document text with source evidence.
                                </div>
                                <div class="message-meta">LegalLens AI</div>
                            </div>
                        </div>

                        <div class="chat-input-area">
                            <form id="qa-form" class="chat-input-row">
                                <textarea id="qa-input" class="chat-input" rows="1"
                                    placeholder="E.g. What is the notice period for termination?"
                                    required autocomplete="off" aria-label="Your question"
                                    maxlength="2000"></textarea>
                                <button type="submit" class="btn btn-primary" id="qa-submit"
                                        aria-label="Send question">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                                         stroke="currentColor" stroke-width="2" aria-hidden="true">
                                        <path stroke-linecap="round" stroke-linejoin="round"
                                              d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/>
                                    </svg>
                                </button>
                            </form>
                            <p class="text-xs text-muted mt-2 text-center">
                                Answers are based on the uploaded document, not general legal knowledge.
                            </p>
                        </div>
                    </div>
                </div>
            `,

            bindEvents(app) {
                const form     = document.getElementById('qa-form');
                const input    = document.getElementById('qa-input');
                const submit   = document.getElementById('qa-submit');
                const messages = document.getElementById('chat-messages');

                // Auto-resize textarea
                input.addEventListener('input', () => {
                    input.style.height = 'auto';
                    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
                });

                // Ctrl+Enter to submit
                input.addEventListener('keydown', (ev) => {
                    if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
                        ev.preventDefault();
                        form.dispatchEvent(new Event('submit'));
                    }
                });

                // Suggested questions
                document.querySelectorAll('.suggested-q').forEach(btn => {
                    btn.addEventListener('click', () => {
                        input.value = btn.dataset.q;
                        input.dispatchEvent(new Event('input'));
                        input.focus();
                    });
                });

                // Submit handler
                form.addEventListener('submit', async (ev) => {
                    ev.preventDefault();
                    const question = input.value.trim();
                    if (!question) return;

                    // User bubble
                    messages.innerHTML += `
                        <div class="message message-user">
                            <div class="message-bubble">${components.escapeHtml(question)}</div>
                        </div>`;
                    input.value = '';
                    input.style.height = 'auto';
                    input.disabled = true;
                    submit.disabled = true;

                    // Loading bubble
                    const loadId = 'load-' + Date.now();
                    messages.innerHTML += `
                        <div id="${loadId}" class="message message-ai">
                            <div class="message-bubble" style="opacity:0.6">
                                <div class="spinner spinner-sm" style="display:inline-block;vertical-align:middle;margin-right:8px"></div>
                                Searching document…
                            </div>
                        </div>`;
                    messages.scrollTop = messages.scrollHeight;

                    try {
                        const res = await api.askQuestion(docId, question);
                        const loaderEl = document.getElementById(loadId);
                        if (loaderEl) loaderEl.remove();

                        const isFallback = res._metadata?.analysis_mode === 'fallback';
                        const groundingLabel = {
                            'grounded': '✓ Grounded in document',
                            'partially_grounded': '~ Partially grounded',
                            'not_found': '✕ Not found in document',
                            'general_info': 'ℹ General information',
                        }[res.grounding_status] || '';

                        let bubble = '';
                        if (isFallback) {
                            bubble += `<div style="background:var(--warning-light);color:var(--warning);padding:var(--space-2) var(--space-3);border-radius:var(--radius-md);font-size:var(--text-xs);font-weight:600;margin-bottom:var(--space-3)">
                                ⚠ Keyword search (AI unavailable)
                            </div>`;
                        }
                        bubble += `<p style="margin:0 0 var(--space-3)">${components.escapeHtml(res.answer)}</p>`;

                        if (res.disclaimer) {
                            bubble += `<p style="font-size:var(--text-xs);color:var(--warning);margin:0 0 var(--space-3);padding:var(--space-2);background:var(--warning-light);border-radius:var(--radius-sm)">
                                ⚖ ${components.escapeHtml(res.disclaimer)}
                            </p>`;
                        }

                        if (res.citations?.length) {
                            bubble += `<div style="border-top:1px solid var(--border-subtle);padding-top:var(--space-3);margin-top:var(--space-3)">
                                <p style="font-size:var(--text-xs);font-weight:600;color:var(--text-muted);margin:0 0 var(--space-2)">SOURCE EVIDENCE</p>`;
                            for (const c of res.citations) bubble += components.citation(c);
                            bubble += '</div>';
                        } else if (res.grounding_status === 'not_found') {
                            bubble += `<p style="font-size:var(--text-xs);color:var(--text-light);margin-top:var(--space-2)">
                                No specific evidence found in the uploaded document.
                            </p>`;
                        }

                        messages.innerHTML += `
                            <div class="message message-ai">
                                <div class="message-bubble">${bubble}</div>
                                <div class="message-meta">${groundingLabel}</div>
                            </div>`;

                    } catch (error) {
                        const loaderEl = document.getElementById(loadId);
                        if (loaderEl) loaderEl.remove();
                        messages.innerHTML += `
                            <div class="message message-ai">
                                <div class="message-bubble" style="color:var(--danger)">
                                    ✕ ${components.escapeHtml(error.message)}
                                </div>
                            </div>`;
                    } finally {
                        input.disabled = false;
                        submit.disabled = false;
                        input.focus();
                        messages.scrollTop = messages.scrollHeight;
                    }
                });
            },
        };
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  CHECKLIST
    // ═══════════════════════════════════════════════════════════════════════════
    checklist(items, isFallback = false) {
        if (!items?.length) {
            return isFallback
                ? components.fallbackNotice() + components.empty('No Checklist Items', 'No clear action items found.')
                : components.empty('No Action Items', 'No specific actions were identified in this document.');
        }

        const itemsHtml = items.map((item, idx) => `
            <div class="checklist-item" id="ci-${idx}">
                <input type="checkbox" class="checklist-checkbox"
                       id="cb-${idx}" aria-labelledby="ca-${idx}"
                       ${item.completed ? 'checked' : ''}>
                <div class="checklist-content">
                    <div class="checklist-action" id="ca-${idx}">${e(item.action)}</div>
                    <div class="checklist-meta">
                        ${item.responsible_party ? `<span>👤 ${e(item.responsible_party)}</span>` : ''}
                        ${item.deadline ? `<span>📅 ${e(item.deadline)}</span>` : ''}
                        ${item.source ? `<span>📑 ${e(item.source)}</span>` : ''}
                    </div>
                </div>
                ${components.priorityBadge(item.priority)}
            </div>
        `).join('');

        return `
            ${isFallback ? components.fallbackNotice(true) : ''}
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
                <h2 style="margin:0">Action Checklist <span class="badge badge-neutral">${items.length} items</span></h2>
                ${isFallback ? components.badge('Document Analysis', 'fallback') : components.badge('AI Enhanced', 'ai')}
            </div>
            <p class="text-sm text-muted mb-5">
                Check off items as you review and address them.
                These are suggested actions based on the document content — verify with your attorney.
            </p>
            <div class="card">
                <div id="checklist-items">
                    ${itemsHtml}
                </div>
            </div>
            <p class="text-xs text-muted mt-3 text-center">
                ⚠ Checklist items are suggestions based on document analysis. Always verify with a qualified legal professional.
            </p>
        `;
    },

    checklistBindEvents() {
        document.getElementById('checklist-items')?.addEventListener('change', (ev) => {
            const cb = ev.target.closest('input[type="checkbox"]');
            if (!cb) return;
            const idx = cb.id.replace('cb-', '');
            const item = document.getElementById(`ci-${idx}`);
            if (item) item.classList.toggle('completed', cb.checked);
        });
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  LAWYER QUESTIONS
    // ═══════════════════════════════════════════════════════════════════════════
    lawyer(questions, isFallback = false) {
        if (!questions?.length) {
            return isFallback
                ? components.fallbackNotice() + components.empty('No Questions Generated', 'Upload a longer document for better results.')
                : components.empty('No Questions Generated', 'No specific issues requiring legal consultation were identified.');
        }

        const items = questions.map((q, i) => `
            <div class="lawyer-question-card">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:var(--space-3);margin-bottom:var(--space-3)">
                    <div class="lawyer-question-text">${i + 1}. "${e(q.question)}"</div>
                    ${components.priorityBadge(q.priority)}
                </div>
                ${q.context ? `<p class="text-sm text-muted mb-2"><strong>Why this matters:</strong> ${e(q.context)}</p>` : ''}
                ${q.related_clause ? `<p class="text-xs text-muted">📑 Related to: ${e(q.related_clause)}</p>` : ''}
            </div>
        `).join('');

        return `
            ${isFallback ? components.fallbackNotice(true) : ''}
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-4)">
                <h2 style="margin:0">Questions for Your Lawyer <span class="badge badge-neutral">${questions.length}</span></h2>
                ${isFallback ? components.badge('Document Analysis', 'fallback') : components.badge('AI Enhanced', 'ai')}
            </div>
            <div class="fallback-notice" style="background:var(--accent-light);border-color:#ddd6fe;color:#4c1d95">
                <span style="font-size:1.25rem;flex-shrink:0">⚖️</span>
                <div>
                    <strong>Important:</strong> These questions are generated to help you have a more productive
                    conversation with a qualified legal professional. They are <em>not</em> legal advice,
                    and LegalLens AI does not answer them on your behalf.
                </div>
            </div>
            ${items}
        `;
    },

    // ═══════════════════════════════════════════════════════════════════════════
    //  DOCUMENT COMPARISON
    // ═══════════════════════════════════════════════════════════════════════════
    compare(documents) {
        const opts = documents.map(d => `<option value="${e(d.id)}">${e(d.filename)}</option>`).join('');

        const noDocsMsg = documents.length < 2
            ? `<div class="fallback-notice" style="background:var(--primary-light);border-color:var(--primary-border);color:var(--primary)">
                   <span style="font-size:1.25rem">ℹ</span>
                   <div>You need at least <strong>two documents</strong> to compare. Upload another document or load the demo first.</div>
               </div>`
            : '';

        return {
            html: `
                <h2 class="mb-2">Compare Documents</h2>
                <p class="text-sm text-muted mb-6">
                    Select two documents to identify key differences in terms, obligations, and provisions.
                </p>

                ${noDocsMsg}

                <div class="card mb-6">
                    <div class="card-header"><h3 style="margin:0">Select Documents</h3></div>
                    <div class="card-body">
                        <form id="compare-form">
                            <div class="compare-grid">
                                <div class="form-group">
                                    <label class="form-label" for="doc-a">Document A (Baseline)</label>
                                    <select id="doc-a" class="form-control" required
                                            ${documents.length < 2 ? 'disabled' : ''}>
                                        <option value="">Select first document…</option>
                                        ${opts}
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="doc-b">Document B (Comparison)</label>
                                    <select id="doc-b" class="form-control" required
                                            ${documents.length < 2 ? 'disabled' : ''}>
                                        <option value="">Select second document…</option>
                                        ${opts}
                                    </select>
                                </div>
                            </div>
                            <div class="text-center mt-4">
                                <button type="submit" class="btn btn-primary" id="compare-btn"
                                        ${documents.length < 2 ? 'disabled' : ''}>
                                    Run Comparison
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <div id="compare-result" aria-live="polite"></div>
            `,

            bindEvents(app) {
                const form       = document.getElementById('compare-form');
                const resultArea = document.getElementById('compare-result');
                const btn        = document.getElementById('compare-btn');

                if (!form) return;

                form.addEventListener('submit', async (ev) => {
                    ev.preventDefault();
                    const docAId = document.getElementById('doc-a').value;
                    const docBId = document.getElementById('doc-b').value;

                    if (!docAId || !docBId) {
                        components.toast('Please select both documents.', 'warning');
                        return;
                    }
                    if (docAId === docBId) {
                        components.toast('Please select two different documents.', 'error');
                        return;
                    }

                    btn.disabled = true;
                    resultArea.innerHTML = components.loader('Comparing documents — this may take up to 30 seconds…');

                    try {
                        const res = await api.compareDocuments(docAId, docBId);
                        const isFallback = res._metadata?.analysis_mode === 'fallback';

                        let html = isFallback ? components.fallbackNotice() : '';

                        html += `
                            <div class="card mb-5">
                                <div class="card-header">
                                    <h3 style="margin:0">Summary of Differences</h3>
                                    ${isFallback ? components.badge('Document Analysis', 'fallback') : components.badge('AI Enhanced', 'ai')}
                                </div>
                                <div class="card-body">
                                    <p class="mb-4">${components.escapeHtml(res.summary)}</p>
                                    ${res.key_differences?.length ? `
                                    <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:var(--space-2)">
                                        ${res.key_differences.map(d =>
                                            `<li style="padding:var(--space-2) var(--space-3);background:var(--bg-alt);border-radius:var(--radius-md);font-size:var(--text-sm)">
                                                • ${components.escapeHtml(d)}
                                            </li>`).join('')}
                                    </ul>` : ''}
                                </div>
                            </div>
                        `;

                        for (const item of (res.items || [])) {
                            const statusMap = { added: 'added', removed: 'removed', changed: 'changed', unchanged: 'unchanged' };
                            const statusCls = statusMap[item.status] || 'neutral';

                            html += `
                                <div class="card mb-4">
                                    <div class="card-header">
                                        <h3 style="margin:0">${components.escapeHtml(item.category)}</h3>
                                        <span class="badge badge-${statusCls}">${components.escapeHtml(item.status?.toUpperCase() || '')}</span>
                                    </div>
                                    <div class="card-body">
                                        <p class="text-sm mb-4" style="color:var(--text-secondary)">${components.escapeHtml(item.explanation)}</p>
                                        <div class="compare-grid">
                                            <div class="compare-side">
                                                <div class="compare-side-label">Document A</div>
                                                <p class="text-sm whitespace-pre">${components.escapeHtml(item.document_a) || '<em>Not present</em>'}</p>
                                            </div>
                                            <div class="compare-side">
                                                <div class="compare-side-label">Document B</div>
                                                <p class="text-sm whitespace-pre">${components.escapeHtml(item.document_b) || '<em>Not present</em>'}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }

                        resultArea.innerHTML = html;

                    } catch (error) {
                        resultArea.innerHTML = `
                            <div class="card card-body text-center">
                                <p style="color:var(--danger)">✕ Comparison failed: ${components.escapeHtml(error.message)}</p>
                            </div>`;
                    } finally {
                        btn.disabled = false;
                    }
                });
            },
        };
    },
};

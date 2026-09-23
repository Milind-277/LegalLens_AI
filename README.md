# LegalLens AI

> Understand your documents. Ask better questions. Navigate legal information with confidence.

LegalLens AI is a production-quality, GenAI-powered legal document assistance application built for
Prompt Wars Challenge 5. It helps users understand, compare, and navigate complex legal documents
while strictly maintaining the boundary between document assistance and professional legal advice.

---

## 📋 Problem Statement Alignment

| Challenge Requirement | LegalLens Feature | Implementation |
|---|---|---|
| Simplifying complex documents | Multi-level Summaries & Key Points | `analysis_service.generate_summary` |
| Comparing contracts | Clause-by-clause Comparison | `comparison_service.compare_documents` |
| Highlighting clauses & risks | Clause Extraction & Review Flags | `analysis_service.extract_clauses` / `analyze_risks` |
| Answering document questions | Document-Grounded Q&A (RAG) | `qa_service.ask_question` |
| Identifying obligations | Obligation extraction with actor/deadline/trigger | `analyze_risks` |
| Understanding next steps | Legal Action Map + Checklist | `analysis_service.generate_checklist` |
| Preparing for a lawyer | Lawyer Question Generation | `analysis_service.generate_lawyer_questions` |
| NOT replacing professional advice | Legal Safety Guardrails & Disclaimers | `ai/safety.py` + prompt system |

---

## 🏗️ Architecture

LegalLens AI uses a clean layered architecture designed for reliability, testability, and evaluator-clarity.

```
Frontend (Vanilla JS + HTML5)
         │ REST API calls
         ▼
Flask API Routes
         │
Security & Error Middleware
         │
Application Services
    ├── DocumentService (upload, process, store, delete)
    ├── AnalysisService (summary, clauses, risks, checklist, lawyer questions)
    ├── QAService       (RAG pipeline + citation validation)
    └── ComparisonService (side-by-side document diff)
         │
AI Pipeline
    ├── AIClient       (Google GenAI + Tenacity retries)
    ├── PromptManager  (system boundary isolation)
    ├── SafetyLayer    (injection detection, advice boundary)
    ├── Retrieval      (TF-IDF chunk scoring)
    ├── Grounding      (citation existence validation)
    └── Parser         (Pydantic-validated structured output)
         │
In-Memory DocumentStore
```

---

## 🛡️ Security Architecture

### 1. Prompt Injection Defense
Document content is isolated using explicit boundary markers in every prompt:
```
--- DOCUMENT CONTENT START ---
[untrusted user document text]
--- DOCUMENT CONTENT END ---
```
A regex-based injection detector also screens the user's question before it reaches the AI.

### 2. Legal Safety Guardrails
- **Advice boundary detection:** Questions asking for legal conclusions ("Is this legal?",
  "Will I win?", "Can I sue?") are detected and redirected with a safe disclaimer.
- **Mandatory disclaimers:** Every response includes a clear AI-assistance disclaimer.
- **Not-found fallback:** If the AI cannot ground an answer, it returns "Not found in the
  provided document" rather than hallucinating.

### 3. Upload Security
- Extension whitelist (PDF, DOCX, TXT only)
- Magic byte / MIME signature validation for PDF
- SHA-256-based duplicate detection
- Path traversal prevention (basename + null byte stripping)
- Configurable file size limits (default 10 MB)
- Dangerous extension rejection (.exe, .js, .sh, etc.)

### 4. Application Hardening
- HTTP security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Custom error handlers — no stack traces ever returned to clients
- Privacy-preserving request logger — never logs document content or API keys
- Per-document delete endpoint so users can remove their data immediately

---

## 🧠 AI Pipeline & Grounding

### RAG Pipeline (Question Answering)
1. Validate and sanitize question
2. Check for legal advice requests → redirect if detected
3. Chunk document with configurable overlap
4. TF-IDF retrieval: score chunks against query, select top-k
5. Assemble bounded context (max 12,000 chars) with source markers
6. Generate AI answer with grounding instructions
7. Validate citations: strip any citation whose text cannot be found in the source document
8. Return answer with grounding status: `grounded` / `partially_grounded` / `not_found`

### Citation Validation
Every citation's text is checked against the original document using:
- Exact substring matching (case-insensitive)
- High-threshold word-overlap fuzzy matching (≥ 85% overlap required)

Citations that cannot be verified are removed and the grounding status is downgraded automatically.
The system never returns a hallucinated page reference.

---

## ♿ Accessibility (WCAG 2.2 AA)

- **Semantic HTML:** `<main>`, `<nav>`, `<header>`, heading hierarchy, skip link
- **Keyboard Navigation:** All interactive elements reachable by keyboard; drop zone supports Enter/Space
- **ARIA:** `aria-live` regions for dynamic Q&A output, alerts, and loading states
- **Legal disclaimer banner:** Persistent `role="alert"` dismissible banner on all pages
- **Focus visible:** All focusable elements have a visible focus ring (`:focus-visible`)
- **Color not sole indicator:** Review flags communicate priority via icon + text + color
- **Reduced motion:** CSS `@media (prefers-reduced-motion)` respected for animations

---

## 🚀 Setup & Execution

### Requirements
- Python 3.11+
- Google Generative AI API Key

### Installation

```bash
# 1. Clone and create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set GOOGLE_API_KEY to your actual key

# 4. Run
python run.py
```

Navigate to `http://localhost:5000` in your browser.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | *(required)* | Google Generative AI API key |
| `FLASK_ENV` | `development` | Flask environment |
| `SECRET_KEY` | *(required)* | Flask session secret |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum upload file size in MB |
| `AI_MODEL_NAME` | `gemini-1.5-flash` | Gemini model to use |
| `AI_MAX_RETRIES` | `3` | Number of retry attempts on API failure |
| `AI_TIMEOUT_SECONDS` | `60` | Request timeout in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/documents` | List uploaded documents |
| `POST` | `/api/documents/upload` | Upload a document (multipart) |
| `GET` | `/api/documents/<id>` | Get document metadata |
| `GET` | `/api/documents/<id>/text` | Get document text |
| `DELETE` | `/api/documents/<id>` | Delete document |
| `GET` | `/api/documents/<id>/summary` | Generate summary |
| `GET` | `/api/documents/<id>/clauses` | Extract clauses |
| `GET` | `/api/documents/<id>/risks` | Identify review flags & obligations |
| `GET` | `/api/documents/<id>/checklist` | Generate action checklist |
| `GET` | `/api/documents/<id>/lawyer-questions` | Generate lawyer questions |
| `POST` | `/api/documents/<id>/ask` | Ask a document question (Q&A) |
| `POST` | `/api/documents/compare` | Compare two documents |

All endpoints return a consistent structure:

```json
{
  "success": true,
  "data": { "..." },
  "error": null,
  "metadata": { "timestamp": "...", "version": "1.0.0" }
}
```

---

## 🧪 Testing & Quality

### Measured Results

| Metric | Value |
|---|---|
| Test count | 245 tests |
| Test coverage | 84% |
| Failing tests | 0 |
| Ruff violations | 0 |
| Black violations | 0 |
| isort violations | 0 |

### Running Tests

```bash
# Run test suite with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Code quality checks
ruff check app/ tests/
black --check app/ tests/
isort --check-only app/ tests/
```

### Test Coverage by Area

| Area | Coverage |
|---|---|
| AI Client (retry, errors, JSON parsing) | 89% |
| AI Parser (all response types) | 85% |
| AI Retrieval (TF-IDF, context assembly) | 98% |
| AI Safety (injection, advice detection) | 100% |
| AI Grounding (citation validation) | 95% |
| AI Prompts | 100% |
| Analysis Service | 90% |
| QA Service | 100% |
| Comparison Service | 100% |
| Document Service (upload, extract, store) | 72% |
| All API Routes | 100% |
| Config | 100% |
| Models | 100% |
| Validators | 92% |

---

## ⚠️ Limitations

- **In-memory storage:** Documents are cleared on server restart. A production deployment
  would use a persistent store (PostgreSQL, Redis, S3).
- **PDF OCR:** `pypdf` can extract text from standard PDFs but cannot read scanned/image PDFs.
  These would require an OCR step.
- **Session isolation:** Multiple users sharing a server instance share the document store.
  A production deployment would require user authentication and per-session isolation.
- **Real-time AI:** All AI calls are synchronous. High-concurrency deployments would benefit
  from task queuing (Celery, RQ).

---

## 📝 Legal Disclaimer

> **This application provides document analysis assistance only.**
> It does not constitute legal advice and is not a substitute for consultation with
> a qualified attorney. Always seek professional legal guidance for your specific situation.
#   L e g a l L e n s _ A I  
 
# LegalLens AI

LegalLens AI is a document-grounded legal information workspace that helps users understand, compare, and navigate legal documents using GenAI, retrieval, structured analysis, and deterministic fallback workflows.

---

## ⚖️ Why LegalLens?

Legal documents are notoriously difficult to understand. Important obligations, risks, and deadlines can be buried in long, complex text. Comparing contracts manually is time-consuming, and individuals often struggle to figure out the right questions to ask a professional. 

LegalLens AI addresses this by providing instant, plain-language summaries, extracting key clauses and obligations, and generating structured checklists and lawyer-ready questions. It simplifies legal navigation without replacing professional counsel.

---

## ✨ Key Features

| Feature | What it does |
|---|---|
| **Document Upload** | Securely upload and parse PDF, DOCX, and TXT files with metadata extraction. |
| **Plain-Language Summary** | Generates clear summaries, key facts, and party identification from complex documents. |
| **Clause Intelligence** | Extracts and categorizes standard legal clauses (e.g., Termination, Liability, NDA). |
| **Review Flags & Obligations** | Highlights potential risks and extracts specific obligations, actors, and deadlines. |
| **Grounded Q&A** | Answers document-specific questions using chunk-based retrieval with strict citation validation. |
| **Document Comparison** | Compares two documents side-by-side, highlighting changes in clauses and text. |
| **Action Checklist** | Generates a structured list of recommended actions and next steps based on the document. |
| **Lawyer Questions** | Prepares context-aware questions to ask a legal professional during a consultation. |
| **Deterministic Fallback** | AI-free, keyword-based analysis fallback when the AI service is unavailable or rate-limited. |
| **Demo Mode** | Built-in demo document loading for easy demonstration and evaluation. |

---

## 🧭 Legal Action Map

The LegalLens AI interface is structured around a practical action workflow:

1. **What the document says:** (Summary & Clauses)
2. **What I may need to do:** (Checklists & Obligations)
3. **What needs review:** (Review Flags)
4. **Questions for a lawyer:** (Lawyer Questions)

This structured approach ensures users focus on actionable insights and understand their responsibilities before signing or agreeing to terms.

---

## 🧠 How LegalLens AI Works

1. **User** uploads a file.
2. **Document Upload:** Validates file type, size, and magic bytes.
3. **Validation & Extraction:** Text is extracted from PDF, DOCX, or TXT. Duplicate detection via SHA-256 prevents redundant processing.
4. **Text Normalization & Chunking:** Text is cleaned and split into manageable chunks with overlap.
5. **Document Storage:** Stored in an in-memory document store.
6. **Retrieval:** TF-IDF based relevant chunk selection.
7. **Gemini / AI Pipeline:** Structured requests sent to the AI.
8. **Structured Validation:** AI responses parsed and validated via Pydantic.
9. **Grounding & Citation Validation:** Citations are cross-checked against the original text. Hallucinated citations are stripped.
10. **Analysis / Q&A / Comparison:** Results are assembled.
11. **UI:** Sent back to the frontend.

---

## 🤖 AI Architecture

The application abstracts the AI interaction through a robust `AIClient`:

- **Google Gemini Integration:** Uses `google-generativeai` (v0.7.2).
- **Structured Output:** Enforces JSON structures and handles markdown code fences safely.
- **Resilience:** Integrates `tenacity` for retries on transient errors (500/503).
- **Fail-Fast:** Quota/rate-limit (429) errors immediately trigger the deterministic fallback pipeline.
- **Validation:** Pydantic is used extensively to validate all AI responses.
- **Deterministic Fallback:** If the AI is unavailable, a keyword/regex-based engine provides summaries, clauses, and QA directly from document text.

---

## 🔎 Retrieval & Grounding

LegalLens AI employs a robust retrieval and grounding pipeline to constrain AI responses and reduce hallucination:

- **Document Chunking:** Text is broken into manageable chunks while preserving context.
- **Deterministic Retrieval:** TF-IDF is used to select the most relevant chunks for Q&A.
- **Citation Generation:** The AI must cite its sources.
- **Citation Validation:** Every citation is rigorously checked against the original document text. If a citation cannot be found via exact or high-threshold fuzzy matching, it is removed.
- **Grounding Status:** Responses are marked as `grounded`, `partially_grounded`, or `not_found`.
- **Unsupported-Answer Handling:** If no relevant information is found, the system explicitly states it rather than guessing.

*Responses are constrained by retrieved document evidence where grounding is required.*

---

## 🛡️ Legal Safety

**LegalLens AI provides informational assistance and document understanding. It does NOT replace a qualified legal professional.**

Safeguards include:
- **Mandatory Disclaimers:** A legal disclaimer is visible on the UI and embedded in generated advice.
- **Document-Grounded Responses:** AI must rely on the document text.
- **Neutral Review Language:** Risk flags are presented neutrally.
- **Lawyer-Question Generation:** Explicitly encourages users to consult professionals.
- **Advice Boundary Detection:** Requests for direct legal advice are detected and gracefully redirected.

---

## 🔐 Security & Privacy

LegalLens implements multiple security controls:

- **Environment Configuration:** API keys are loaded via `.env` (never hardcoded).
- **Upload Validation:** Strict file extension, size limits, and magic-byte validation.
- **Filename Sanitization:** Path traversal protection.
- **Security Headers:** Enforces CSP, HSTS, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy.
- **Privacy-Aware Logging:** Sensitive document content and API keys are completely excluded from logs.
- **Prompt Injection Defense:** Document content is clearly demarcated in prompts to prevent instruction override.

---

## 🧪 Testing & Quality

LegalLens AI includes a comprehensive test suite.

**Current Metrics (Verified):**
- **Test Count:** 247 tests
- **Test Coverage:** 84%
- **Failing Tests:** 0
- **Ruff Violations:** 30 errors found (mostly line length)
- **Black Violations:** 1 file needs reformatting
- **isort Violations:** 0

**Commands to Verify:**

```bash
# Run tests with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Linting and formatting checks
ruff check app/ tests/
black --check app/ tests/
isort --check-only app/ tests/
```

---

## 🚀 Setup & Running Locally

### Requirements
- Python 3.11+
- Google Gemini API Key

### Installation

1. **Clone and setup virtual environment:**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Environment Setup:**
```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

4. **Run the application:**
```bash
python run.py
```

Access the application at `http://localhost:5000`.

### Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Your Google Generative AI key |
| `FLASK_ENV` | Environment (e.g., `development`) |
| `SECRET_KEY` | Flask session secret |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed file size for uploads (default: 10) |
| `AI_MAX_RETRIES` | Number of retries for transient AI errors |

---

## ⚠️ Limitations & Future Improvements

- **In-Memory Storage:** The current `DocumentStore` is session-scoped and in-memory. A production version would require persistent storage (e.g., PostgreSQL).
- **OCR Support:** Currently relies on `pypdf` for text extraction, which does not support scanned documents.
- **AI SDK:** Currently using `google-generativeai==0.7.2`; future iterations could migrate to the newer `google.genai` SDK.
- **Queueing:** Synchronous processing; a production deployment should move heavy extraction and AI generation to background workers (e.g., Celery).

---

## 📄 License
Check the repository for specific licensing details (if applicable).
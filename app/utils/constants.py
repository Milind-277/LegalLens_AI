"""LegalLens AI — Application constants."""

# --- File Processing ---
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx", "txt"})

MIME_SIGNATURES: dict[str, list[bytes]] = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04"],  # ZIP-based format
    "txt": [],  # No magic bytes for plaintext
}

MAX_FILENAME_LENGTH: int = 255

# --- Document Processing ---
CHUNK_SIZE: int = 1500
CHUNK_OVERLAP: int = 200
MAX_DOCUMENT_CHARS: int = 500_000
MIN_DOCUMENT_CHARS: int = 10
MAX_CHUNKS_PER_DOCUMENT: int = 500

# --- AI ---
AI_MAX_CONTEXT_CHUNKS: int = 10
AI_MAX_RETRIES: int = 3
AI_TIMEOUT_SECONDS: int = 60

# --- Clause Categories ---
CLAUSE_CATEGORIES: list[str] = [
    "Parties",
    "Term / Duration",
    "Payment",
    "Renewal",
    "Termination",
    "Confidentiality",
    "Intellectual Property",
    "Privacy / Data Protection",
    "Liability",
    "Indemnity",
    "Dispute Resolution",
    "Governing Law",
    "Notices",
    "Restrictions / Non-Compete",
    "Force Majeure",
    "Amendments",
    "Assignment",
    "Warranties",
    "Insurance",
    "Other Important Provisions",
]

# --- Risk / Review Levels ---
REVIEW_LEVELS: list[str] = ["LOW", "MEDIUM", "HIGH", "REVIEW"]

# --- Summary Types ---
SUMMARY_TYPES: list[str] = ["quick", "detailed", "executive"]

# --- API Response Codes ---
ERROR_CODES: dict[str, str] = {
    "VALIDATION_ERROR": "Request validation failed",
    "FILE_TOO_LARGE": "File exceeds maximum allowed size",
    "UNSUPPORTED_FORMAT": "File format is not supported",
    "EMPTY_FILE": "File contains no extractable text",
    "CORRUPTED_FILE": "File appears to be corrupted or unreadable",
    "DOCUMENT_NOT_FOUND": "Document not found",
    "DUPLICATE_DOCUMENT": "This document has already been uploaded",
    "PROCESSING_FAILED": "Document processing failed",
    "AI_UNAVAILABLE": "AI service is temporarily unavailable",
    "AI_ERROR": "AI processing encountered an error",
    "RATE_LIMITED": "Too many requests, please try again later",
    "INTERNAL_ERROR": "An internal error occurred",
}

# --- Legal Safety ---
LEGAL_DISCLAIMER: str = (
    "LegalLens AI provides legal information and document analysis assistance. "
    "It does NOT provide legal advice and is NOT a substitute for a qualified "
    "legal professional. Always consult with a licensed attorney for legal advice "
    "specific to your situation."
)

ADVICE_REDIRECT: str = (
    "I can provide document-based information and general educational context, "
    "but a qualified legal professional should advise you on your specific situation."
)

# --- Security ---
DANGEROUS_EXTENSIONS: frozenset[str] = frozenset(
    {
        "exe",
        "bat",
        "cmd",
        "sh",
        "ps1",
        "vbs",
        "js",
        "msi",
        "dll",
        "com",
        "scr",
        "pif",
        "jar",
        "py",
        "rb",
        "pl",
        "php",
        "asp",
        "aspx",
        "jsp",
    }
)

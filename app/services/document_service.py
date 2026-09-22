"""LegalLens AI — Document processing service."""

from __future__ import annotations

import io
from typing import Any

import structlog

from app.models.document import Document, DocumentMetadata, ProcessingStatus
from app.utils.constants import MAX_DOCUMENT_CHARS, MIN_DOCUMENT_CHARS
from app.utils.text_processing import (
    chunk_text,
    extract_page_breaks,
    normalize_text,
)
from app.utils.validators import (
    ValidationError,
    compute_file_hash,
    generate_document_id,
    sanitize_filename,
    validate_file_extension,
    validate_file_not_empty,
    validate_file_size,
    validate_magic_bytes,
)

logger = structlog.get_logger(__name__)


class DocumentStore:
    """In-memory document store (session-scoped).

    For a production deployment this would use a database,
    but for this challenge an in-memory store is appropriate and efficient.
    """

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._hashes: dict[str, str] = {}  # hash -> doc_id

    def add(self, doc: Document) -> None:
        """Store a document."""
        self._documents[doc.id] = doc
        self._hashes[doc.file_hash] = doc.id

    def get(self, doc_id: str) -> Document | None:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    def get_by_hash(self, file_hash: str) -> str | None:
        """Check if a document with this hash already exists. Returns doc_id or None."""
        return self._hashes.get(file_hash)

    def list_all(self) -> list[dict[str, Any]]:
        """List all documents (summary view)."""
        return [doc.to_summary_dict() for doc in self._documents.values()]

    def delete(self, doc_id: str) -> bool:
        """Delete a document. Returns True if found and deleted."""
        doc = self._documents.pop(doc_id, None)
        if doc:
            self._hashes.pop(doc.file_hash, None)
            return True
        return False

    def count(self) -> int:
        """Return number of stored documents."""
        return len(self._documents)


# Module-level store instance
document_store = DocumentStore()


def process_upload(
    file_bytes: bytes,
    filename: str,
    max_size_bytes: int,
) -> Document:
    """Process an uploaded document file.

    Validates, extracts text, chunks, and stores the document.

    Args:
        file_bytes: Raw file content.
        filename: Original filename.
        max_size_bytes: Maximum allowed file size.

    Returns:
        Processed Document.

    Raises:
        ValidationError: If validation fails.
    """
    # Step 1: Validate
    validate_file_not_empty(file_bytes)
    validate_file_size(file_bytes, max_size_bytes)
    safe_filename = sanitize_filename(filename)
    extension = validate_file_extension(safe_filename)
    validate_magic_bytes(file_bytes, extension)

    # Step 2: Check for duplicates
    file_hash = compute_file_hash(file_bytes)
    existing_id = document_store.get_by_hash(file_hash)
    if existing_id:
        raise ValidationError(
            "DUPLICATE_DOCUMENT",
            f"This document has already been uploaded (ID: {existing_id})",
        )

    # Step 3: Create document record
    doc_id = generate_document_id()
    doc = Document(
        id=doc_id,
        filename=safe_filename,
        file_type=extension,
        file_hash=file_hash,
        file_size=len(file_bytes),
        status=ProcessingStatus.PROCESSING,
    )

    logger.info(
        "document_processing_started", doc_id=doc_id, filename=safe_filename, size=len(file_bytes)
    )

    try:
        # Step 4: Extract text
        if extension == "pdf":
            full_text, page_breaks, page_count = _extract_pdf(file_bytes)
        elif extension == "docx":
            full_text, page_breaks, page_count = _extract_docx(file_bytes)
        else:
            full_text, page_breaks, page_count = _extract_txt(file_bytes)

        # Step 5: Normalize
        full_text = normalize_text(full_text)

        if len(full_text.strip()) < MIN_DOCUMENT_CHARS:
            raise ValidationError(
                "EMPTY_FILE",
                "Document contains no extractable text or is too short to analyze.",
            )

        # Truncate extremely long documents
        if len(full_text) > MAX_DOCUMENT_CHARS:
            full_text = full_text[:MAX_DOCUMENT_CHARS]
            logger.warning("document_truncated", doc_id=doc_id, original_length=len(full_text))

        # Step 6: Chunk
        chunks = chunk_text(full_text, page_breaks=page_breaks)

        # Step 7: Build metadata
        sections = list({c.section for c in chunks if c.section})
        metadata = DocumentMetadata(
            page_count=page_count,
            word_count=len(full_text.split()),
            char_count=len(full_text),
            detected_type=_detect_document_type(full_text),
            sections=sorted(sections),
            has_dates=bool(_has_dates(full_text)),
        )

        # Step 8: Finalize
        doc.full_text = full_text
        doc.chunks = chunks
        doc.metadata = metadata
        doc.status = ProcessingStatus.COMPLETED

        document_store.add(doc)

        logger.info(
            "document_processing_completed",
            doc_id=doc_id,
            chunks=len(chunks),
            words=metadata.word_count,
        )

        return doc

    except ValidationError:
        raise
    except Exception as exc:
        doc.status = ProcessingStatus.FAILED
        doc.error_message = "Document processing failed. The file may be corrupted."
        document_store.add(doc)
        logger.error("document_processing_failed", doc_id=doc_id, error=str(exc))
        raise ValidationError("PROCESSING_FAILED", doc.error_message) from exc


def _extract_pdf(file_bytes: bytes) -> tuple[str, list[int], int]:
    """Extract text from PDF."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

        full_text, page_breaks = extract_page_breaks(pages_text)
        return full_text, page_breaks, len(reader.pages)

    except ImportError as exc:
        raise ValidationError(
            "PROCESSING_FAILED",
            "PDF processing requires the 'pypdf' library.",
        ) from exc
    except Exception as exc:
        raise ValidationError(
            "CORRUPTED_FILE",
            "Failed to read PDF file. It may be corrupted or password-protected.",
        ) from exc


def _extract_docx(file_bytes: bytes) -> tuple[str, list[int], int]:
    """Extract text from DOCX."""
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        return full_text, [], 0  # DOCX doesn't have reliable page info

    except ImportError as exc:
        raise ValidationError(
            "PROCESSING_FAILED",
            "DOCX processing requires the 'python-docx' library.",
        ) from exc
    except Exception as exc:
        raise ValidationError(
            "CORRUPTED_FILE",
            "Failed to read DOCX file. It may be corrupted.",
        ) from exc


def _extract_txt(file_bytes: bytes) -> tuple[str, list[int], int]:
    """Extract text from TXT file."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception as exc:
            raise ValidationError(
                "CORRUPTED_FILE",
                "Failed to decode text file. Unsupported encoding.",
            ) from exc

    return text, [], 0


def _detect_document_type(text: str) -> str:
    """Heuristic detection of document type from text content."""
    text_lower = text.lower()

    indicators = {
        "Employment Agreement": [
            "employment agreement",
            "employee",
            "employer",
            "salary",
            "termination of employment",
        ],
        "Non-Disclosure Agreement": [
            "non-disclosure",
            "nda",
            "confidential information",
            "disclosing party",
            "receiving party",
        ],
        "Service Agreement": [
            "service agreement",
            "service provider",
            "scope of services",
            "service level",
        ],
        "Lease Agreement": ["lease agreement", "landlord", "tenant", "rent", "premises"],
        "Terms of Service": [
            "terms of service",
            "terms and conditions",
            "user agreement",
            "acceptable use",
        ],
        "Privacy Policy": ["privacy policy", "personal data", "data protection", "cookies", "gdpr"],
        "License Agreement": ["license agreement", "licensee", "licensor", "intellectual property"],
        "Partnership Agreement": ["partnership agreement", "partner", "profit sharing"],
        "Sales Contract": ["purchase agreement", "buyer", "seller", "purchase price"],
    }

    best_match = "Legal Document"
    best_score = 0

    for doc_type, keywords in indicators.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_match = doc_type

    return best_match if best_score >= 2 else "Legal Document"


def _has_dates(text: str) -> bool:
    """Check if text contains date-like patterns."""
    import re

    date_patterns = [
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    ]
    return any(re.search(pattern, text) for pattern in date_patterns)

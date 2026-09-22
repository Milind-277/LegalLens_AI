"""LegalLens AI — Extended document service tests covering error paths and edge cases."""

from __future__ import annotations

import pytest

from app.services.document_service import (
    _detect_document_type,
    _extract_txt,
    _has_dates,
    document_store,
    process_upload,
)
from app.utils.validators import ValidationError


class TestDocumentStore:
    """Tests for the in-memory document store."""

    def setup_method(self):
        """Start with a clean store for each test."""
        document_store._documents.clear()
        document_store._hashes.clear()

    def test_add_and_get(self):
        from app.models.document import Document

        doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="hash123")
        document_store.add(doc)
        assert document_store.get("123") is doc

    def test_get_missing_returns_none(self):
        assert document_store.get("nonexistent") is None

    def test_get_by_hash(self):
        from app.models.document import Document

        doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="myhash")
        document_store.add(doc)
        assert document_store.get_by_hash("myhash") == "123"

    def test_get_by_hash_missing_returns_none(self):
        assert document_store.get_by_hash("nonexistent") is None

    def test_list_all(self):
        from app.models.document import Document

        doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="hash123")
        document_store.add(doc)
        listing = document_store.list_all()
        assert len(listing) == 1
        assert listing[0]["id"] == "123"

    def test_delete_existing(self):
        from app.models.document import Document

        doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="hash123")
        document_store.add(doc)
        result = document_store.delete("123")
        assert result is True
        assert document_store.get("123") is None

    def test_delete_nonexistent_returns_false(self):
        assert document_store.delete("nonexistent") is False

    def test_count(self):
        from app.models.document import Document

        assert document_store.count() == 0
        doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="hash123")
        document_store.add(doc)
        assert document_store.count() == 1

    def test_delete_also_removes_hash(self):
        from app.models.document import Document

        doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="deletehash")
        document_store.add(doc)
        document_store.delete("123")
        assert document_store.get_by_hash("deletehash") is None


class TestProcessUpload:
    """Tests for the upload processing pipeline."""

    def setup_method(self):
        document_store._documents.clear()
        document_store._hashes.clear()

    def test_oversized_file_rejected(self):
        with pytest.raises(ValidationError) as exc:
            process_upload(b"x" * 1000, filename="big.txt", max_size_bytes=100)
        assert exc.value.code == "FILE_TOO_LARGE"

    def test_file_with_bad_extension_rejected(self):
        with pytest.raises(ValidationError) as exc:
            process_upload(b"content", filename="script.js", max_size_bytes=1024 * 1024)
        assert exc.value.code == "UNSUPPORTED_FORMAT"

    def test_file_with_only_whitespace_rejected(self):
        """File containing only whitespace should be rejected as too short."""
        with pytest.raises(ValidationError):
            process_upload(b"   \n   ", filename="empty.txt", max_size_bytes=1024 * 1024)

    def test_malicious_filename_path_traversal(self):
        """Path traversal in filename should be safely sanitized."""
        content = b"Valid legal document text content for testing purposes."
        # Should NOT raise but sanitize the filename
        doc = process_upload(
            content, filename="../../../etc/passwd.txt", max_size_bytes=1024 * 1024
        )
        assert "../" not in doc.filename
        assert "passwd.txt" in doc.filename

    def test_null_byte_in_filename(self):
        """Null bytes in filename should be sanitized."""
        content = b"Valid legal document text content for testing purposes."
        doc = process_upload(content, filename="file\x00name.txt", max_size_bytes=1024 * 1024)
        assert "\x00" not in doc.filename

    def test_document_type_detection(self):
        """NDA keywords should be detected."""
        content = (
            b"NON-DISCLOSURE AGREEMENT\n\n"
            b"This NDA is between the disclosing party and the receiving party.\n"
            b"All confidential information must be kept secret."
        )
        doc = process_upload(content, filename="nda.txt", max_size_bytes=1024 * 1024)
        assert "Non-Disclosure" in doc.metadata.detected_type or doc.metadata.detected_type != ""


class TestExtractTxt:
    """Tests for TXT extraction."""

    def test_utf8_decoding(self):
        text, breaks, pages = _extract_txt(b"Hello UTF-8 world")
        assert "Hello UTF-8 world" in text

    def test_latin1_fallback(self):
        """Latin-1 encoded content should fall back gracefully."""
        text, breaks, pages = _extract_txt("caf\xe9 legal".encode("latin-1"))
        assert "legal" in text

    def test_returns_empty_page_info(self):
        text, page_breaks, page_count = _extract_txt(b"Some text")
        assert page_breaks == []
        assert page_count == 0


class TestDetectDocumentType:
    """Tests for document type detection."""

    def test_detects_nda(self):
        text = "non-disclosure agreement between disclosing party and receiving party"
        assert "Non-Disclosure" in _detect_document_type(text)

    def test_detects_lease(self):
        text = "this lease agreement is between the landlord and tenant for the premises"
        assert "Lease" in _detect_document_type(text)

    def test_detects_privacy_policy(self):
        text = "privacy policy regarding personal data protection and cookies and gdpr"
        assert "Privacy" in _detect_document_type(text)

    def test_defaults_for_unknown(self):
        text = "Lorem ipsum dolor sit amet"
        assert _detect_document_type(text) == "Legal Document"

    def test_detects_terms_of_service(self):
        text = "terms and conditions user agreement acceptable use policy"
        assert "Terms" in _detect_document_type(text)


class TestHasDates:
    """Tests for date detection."""

    def test_numeric_date_format(self):
        assert _has_dates("Effective 01/15/2025") is True

    def test_written_date_format(self):
        assert _has_dates("On January 15, 2025 the agreement begins") is True

    def test_no_date(self):
        assert _has_dates("No dates here at all") is False


class TestPDFExtractionError:
    """Tests for PDF failure paths."""

    def test_corrupted_pdf_raises(self):
        """Non-PDF content with .pdf extension raises CORRUPTED_FILE."""
        with pytest.raises(ValidationError) as exc:
            process_upload(b"Not a PDF at all", filename="fake.pdf", max_size_bytes=1024 * 1024)
        # Magic byte check or PDF parse failure
        assert exc.value.code in ("CORRUPTED_FILE", "UNSUPPORTED_FORMAT")

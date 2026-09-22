"""LegalLens AI — Tests for document service."""

import pytest

from app.models.document import ProcessingStatus
from app.services.document_service import document_store, process_upload
from app.utils.validators import ValidationError


def test_process_upload_txt(sample_txt_bytes):
    """Test standard TXT upload processing."""
    doc = process_upload(
        file_bytes=sample_txt_bytes,
        filename="contract.txt",
        max_size_bytes=1024 * 1024,
    )

    assert doc.status == ProcessingStatus.COMPLETED
    assert doc.filename == "contract.txt"
    assert doc.file_type == "txt"
    assert len(doc.full_text) > 50
    assert len(doc.chunks) > 0
    assert any("CONFIDENTIALITY" in s for s in doc.metadata.sections)

    # Verify it was added to store
    stored = document_store.get(doc.id)
    assert stored is not None
    assert stored.id == doc.id


def test_process_upload_empty():
    """Test rejecting empty files."""
    with pytest.raises(ValidationError) as exc:
        process_upload(
            file_bytes=b"",
            filename="empty.txt",
            max_size_bytes=1024,
        )
    assert exc.value.code == "EMPTY_FILE"


def test_process_upload_duplicate(sample_txt_bytes):
    """Test rejecting duplicate files."""
    # First upload
    process_upload(
        file_bytes=sample_txt_bytes,
        filename="contract.txt",
        max_size_bytes=1024 * 1024,
    )

    # Second upload should fail
    with pytest.raises(ValidationError) as exc:
        process_upload(
            file_bytes=sample_txt_bytes,
            filename="copy.txt",
            max_size_bytes=1024 * 1024,
        )
    assert exc.value.code == "DUPLICATE_DOCUMENT"


def test_process_upload_invalid_extension(sample_txt_bytes):
    """Test rejecting invalid extensions."""
    with pytest.raises(ValidationError) as exc:
        process_upload(
            file_bytes=sample_txt_bytes,
            filename="script.js",
            max_size_bytes=1024 * 1024,
        )
    assert exc.value.code == "UNSUPPORTED_FORMAT"

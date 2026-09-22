"""LegalLens AI — Tests for validators."""

import pytest

from app.utils.validators import (
    ValidationError,
    compute_file_hash,
    sanitize_filename,
    validate_file_extension,
    validate_file_not_empty,
    validate_file_size,
    validate_question,
)


def test_sanitize_filename():
    """Test filename sanitization against path traversal and bad chars."""
    assert sanitize_filename("normal.pdf") == "normal.pdf"
    assert sanitize_filename("../../../etc/passwd.txt") == "passwd.txt"
    assert sanitize_filename("my document!.docx") == "my document.docx"

    # Hidden files
    assert sanitize_filename(".hidden.txt") == "hidden.txt"

    # Null bytes
    assert sanitize_filename("file\x00name.pdf") == "filename.pdf"


def test_sanitize_filename_rejects_dangerous():
    """Test that dangerous extensions are rejected."""
    with pytest.raises(ValidationError) as exc:
        sanitize_filename("script.js")
    assert "not allowed" in str(exc.value)

    with pytest.raises(ValidationError):
        sanitize_filename("app.exe")

    with pytest.raises(ValidationError):
        sanitize_filename("C:\\Windows\\System32\\cmd.exe")


def test_validate_file_extension():
    """Test allowed extensions."""
    assert validate_file_extension("doc.pdf") == "pdf"
    assert validate_file_extension("doc.docx") == "docx"
    assert validate_file_extension("doc.TXT") == "txt"

    with pytest.raises(ValidationError):
        validate_file_extension("doc.md")


def test_validate_file_size():
    """Test size validation."""
    validate_file_size(b"a" * 10, max_size_bytes=100)

    with pytest.raises(ValidationError):
        validate_file_size(b"a" * 101, max_size_bytes=100)


def test_validate_file_not_empty():
    """Test empty file validation."""
    validate_file_not_empty(b"content")

    with pytest.raises(ValidationError):
        validate_file_not_empty(b"")

    with pytest.raises(ValidationError):
        validate_file_not_empty(None)


def test_compute_file_hash():
    """Test hash computation."""
    h1 = compute_file_hash(b"test content")
    h2 = compute_file_hash(b"test content")
    h3 = compute_file_hash(b"different content")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA-256


def test_validate_question():
    """Test question validation."""
    assert validate_question(" What is the term? ") == "What is the term?"

    with pytest.raises(ValidationError):
        validate_question("")

    with pytest.raises(ValidationError):
        validate_question("   ")

    with pytest.raises(ValidationError):
        validate_question("a" * 2001)

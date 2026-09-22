"""LegalLens AI — Input validation utilities."""

from __future__ import annotations

import hashlib
import os
import re
import uuid

from app.utils.constants import (
    ALLOWED_EXTENSIONS,
    DANGEROUS_EXTENSIONS,
    MAX_FILENAME_LENGTH,
    MIME_SIGNATURES,
)


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def generate_document_id() -> str:
    """Generate a unique document identifier."""
    return uuid.uuid4().hex


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and other attacks.

    - Strips directory components
    - Removes dangerous characters
    - Limits length
    - Rejects dangerous extensions
    """
    if not filename:
        raise ValidationError("VALIDATION_ERROR", "Filename is empty")

    # Strip directory separators — prevent path traversal
    filename = os.path.basename(filename)
    filename = filename.replace("\\", "").replace("/", "")

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")

    if not filename:
        raise ValidationError("VALIDATION_ERROR", "Filename is invalid after sanitization")

    # Split name and extension
    name, ext = os.path.splitext(filename)

    # Remove non-alphanumeric characters except hyphens, underscores, dots, spaces
    name = re.sub(r"[^\w\s\-.]", "", name).strip()

    if not name:
        name = "document"

    # Truncate
    if len(name) > MAX_FILENAME_LENGTH - len(ext):
        name = name[: MAX_FILENAME_LENGTH - len(ext)]

    ext_lower = ext.lstrip(".").lower()

    # Reject dangerous extensions
    if ext_lower in DANGEROUS_EXTENSIONS:
        raise ValidationError("UNSUPPORTED_FORMAT", f"File type '.{ext_lower}' is not allowed")

    return f"{name}{ext}"


def validate_file_extension(filename: str) -> str:
    """Validate file has an allowed extension. Returns the extension."""
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationError(
            "UNSUPPORTED_FORMAT",
            f"File type '.{ext}' is not supported. Allowed: {allowed}",
        )
    return ext


def validate_file_size(file_bytes: bytes, max_size_bytes: int) -> None:
    """Validate file size against maximum."""
    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(
            "FILE_TOO_LARGE",
            f"File exceeds maximum size of {max_mb:.0f}MB",
        )


def validate_magic_bytes(file_bytes: bytes, extension: str) -> None:
    """Validate file content matches expected format via magic bytes."""
    signatures = MIME_SIGNATURES.get(extension, [])
    if not signatures:
        return  # No signature check for this type (e.g., txt)

    for sig in signatures:
        if file_bytes[: len(sig)] == sig:
            return

    raise ValidationError(
        "CORRUPTED_FILE",
        f"File content does not match expected format for '.{extension}'",
    )


def validate_file_not_empty(file_bytes: bytes) -> None:
    """Validate file is not empty."""
    if not file_bytes or len(file_bytes) == 0:
        raise ValidationError("EMPTY_FILE", "Uploaded file is empty")


def compute_file_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash for deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


def validate_question(question: str) -> str:
    """Validate and sanitize a user question."""
    if not question or not question.strip():
        raise ValidationError("VALIDATION_ERROR", "Question cannot be empty")

    question = question.strip()

    if len(question) > 2000:
        raise ValidationError(
            "VALIDATION_ERROR", "Question exceeds maximum length of 2000 characters"
        )

    return question

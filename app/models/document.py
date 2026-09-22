"""LegalLens AI — Document models."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ProcessingStatus(str, enum.Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentChunk(BaseModel):
    """A chunk of document text with source metadata."""

    chunk_id: int = Field(description="Chunk index within document")
    text: str = Field(description="Chunk text content")
    page: int | None = Field(default=None, description="Source page number (1-indexed)")
    section: str | None = Field(default=None, description="Detected section heading")
    start_char: int = Field(default=0, description="Start character offset in full text")
    end_char: int = Field(default=0, description="End character offset in full text")


class DocumentMetadata(BaseModel):
    """Extracted document metadata."""

    page_count: int = Field(default=0, description="Number of pages (PDF)")
    word_count: int = Field(default=0, description="Approximate word count")
    char_count: int = Field(default=0, description="Character count")
    detected_type: str = Field(default="unknown", description="Detected document type")
    sections: list[str] = Field(default_factory=list, description="Detected section headings")
    has_dates: bool = Field(default=False, description="Whether dates were detected")
    language: str = Field(default="en", description="Detected language")


class Document(BaseModel):
    """Uploaded document representation."""

    id: str = Field(description="Unique document identifier (UUID)")
    filename: str = Field(description="Sanitized original filename")
    file_type: str = Field(description="File extension (pdf, docx, txt)")
    file_hash: str = Field(description="SHA-256 hash for deduplication")
    file_size: int = Field(default=0, description="File size in bytes")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: str | None = Field(
        default=None, description="Error message if processing failed"
    )
    full_text: str = Field(default="", description="Extracted full text")
    chunks: list[DocumentChunk] = Field(default_factory=list, description="Text chunks")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Upload timestamp ISO 8601",
    )

    def to_summary_dict(self) -> dict:
        """Return document info without full text (for list endpoints)."""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status.value,
            "error_message": self.error_message,
            "metadata": {
                "page_count": self.metadata.page_count,
                "word_count": self.metadata.word_count,
                "char_count": self.metadata.char_count,
                "detected_type": self.metadata.detected_type,
                "sections": self.metadata.sections,
            },
            "uploaded_at": self.uploaded_at,
        }

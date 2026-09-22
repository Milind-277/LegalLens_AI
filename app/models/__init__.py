"""LegalLens AI — Models package."""

from app.models.analysis import (
    ChecklistItem,
    Citation,
    Clause,
    ComparisonItem,
    ComparisonResult,
    DocumentAnalysis,
    DocumentSummary,
    LawyerQuestion,
    Obligation,
    QAResponse,
    ReviewFlag,
)
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    ProcessingStatus,
)
from app.models.responses import APIResponse, ErrorDetail

__all__ = [
    "APIResponse",
    "ChecklistItem",
    "Citation",
    "Clause",
    "ComparisonItem",
    "ComparisonResult",
    "Document",
    "DocumentAnalysis",
    "DocumentChunk",
    "DocumentMetadata",
    "DocumentSummary",
    "ErrorDetail",
    "LawyerQuestion",
    "Obligation",
    "ProcessingStatus",
    "QAResponse",
    "ReviewFlag",
]

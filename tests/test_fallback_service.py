"""Tests for deterministic fallback service."""

from app.models.document import Document
from app.services.fallback_service import (
    analyze_fallback_risks,
    extract_fallback_clauses,
    generate_fallback_summary,
)


def test_generate_fallback_summary():
    """Test fallback summary generation."""
    doc = Document(
        id="test-id",
        filename="test.txt",
        content_type="text/plain",
        file_type="txt",
        file_hash="123",
        metadata={"detected_type": "Contract"},
    )
    doc.full_text = "This is a test document.\nIt is an agreement between A and B."

    summary = generate_fallback_summary(doc)
    assert "This is a test document" in summary.quick_summary
    assert "AI analysis is temporarily unavailable" in summary.executive_summary
    assert summary.document_type == "Contract"


def test_extract_fallback_clauses():
    """Test fallback clause extraction."""
    doc = Document(
        id="test", filename="test.txt", content_type="txt", file_type="txt", file_hash="1"
    )
    doc.full_text = "Standard Document.\n\nThis is a confidentiality clause and we agree to a non-disclosure of the information herein."

    clauses = extract_fallback_clauses(doc)
    assert len(clauses) > 0
    assert any(c.category == "Confidentiality" for c in clauses)


def test_analyze_fallback_risks():
    """Test fallback risk analysis."""
    doc = Document(
        id="test", filename="test.txt", content_type="txt", file_type="txt", file_hash="1"
    )
    doc.full_text = "This is a document.\n\nAny breach will result in a penalty of $500.\n\nThe user must pay the fee immediately."

    flags, obligations = analyze_fallback_risks(doc)

    assert any(f.title == "Penalty / Liquidated Damages" for f in flags)
    assert len(obligations) >= 1

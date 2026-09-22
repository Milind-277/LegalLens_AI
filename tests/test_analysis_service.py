"""LegalLens AI — Tests for analysis services."""

import json

from app.models.document import Document
from app.services.analysis_service import (
    analyze_risks,
    extract_clauses,
    generate_summary,
)


def test_generate_summary(mock_ai_client):
    """Test summary generation."""
    doc = Document(
        id="123",
        filename="test.txt",
        file_type="txt",
        file_hash="hash",
        full_text="Test content",
    )

    mock_ai_client.generate.return_value = json.dumps(
        {
            "quick_summary": "Quick",
            "detailed_summary": "Detailed",
        }
    )

    summary = generate_summary(doc, mock_ai_client)
    assert summary.quick_summary == "Quick"

    # Second call should use cache
    mock_ai_client.generate.return_value = '{"quick_summary": "Different"}'
    summary2 = generate_summary(doc, mock_ai_client)
    assert summary2.quick_summary == "Quick"  # Still cached


def test_extract_clauses(mock_ai_client):
    """Test clause extraction."""
    doc = Document(
        id="123",
        filename="test.txt",
        file_type="txt",
        file_hash="hash",
        full_text="Test content",
    )

    mock_ai_client.generate.return_value = json.dumps(
        {
            "clauses": [
                {
                    "category": "Payment",
                    "explanation": "Pay money",
                }
            ]
        }
    )

    clauses = extract_clauses(doc, mock_ai_client)
    assert len(clauses) == 1
    assert clauses[0].category == "Payment"


def test_analyze_risks(mock_ai_client):
    """Test risk analysis."""
    doc = Document(
        id="123",
        filename="test.txt",
        file_type="txt",
        file_hash="hash",
        full_text="Test content",
    )

    mock_ai_client.generate.return_value = json.dumps(
        {
            "review_flags": [
                {"title": "Unclear wording", "explanation": "Not clear", "review_priority": "HIGH"}
            ],
            "obligations": [],
        }
    )

    flags, obligations = analyze_risks(doc, mock_ai_client)
    assert len(flags) == 1
    assert flags[0].title == "Unclear wording"
    assert len(obligations) == 0

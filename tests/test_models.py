"""LegalLens AI — Tests for models."""

from app.models.analysis import Citation, Clause
from app.models.document import Document
from app.models.responses import APIResponse


def test_api_response_ok():
    """Test success response envelope."""
    resp = APIResponse.ok(data={"key": "value"})
    assert resp.success is True
    assert resp.data == {"key": "value"}
    assert resp.error is None

    dump = resp.model_dump()
    assert dump["success"] is True
    assert dump["data"] == {"key": "value"}


def test_api_response_fail():
    """Test failure response envelope."""
    resp = APIResponse.fail(code="ERR", message="Failed")
    assert resp.success is False
    assert resp.data is None
    assert resp.error is not None
    assert resp.error.code == "ERR"
    assert resp.error.message == "Failed"


def test_document_summary_dict():
    """Test document serialization for list views."""
    doc = Document(
        id="123",
        filename="test.txt",
        file_type="txt",
        file_hash="hash",
        file_size=100,
    )

    summary = doc.to_summary_dict()
    assert summary["id"] == "123"
    assert summary["filename"] == "test.txt"
    assert "full_text" not in summary  # Ensure heavy text isn't serialized


def test_citation_model():
    """Test citation model defaults."""
    cit = Citation(text="evidence")
    assert cit.page is None
    assert cit.section is None
    assert cit.text == "evidence"


def test_clause_model():
    """Test clause model initialization."""
    clause = Clause(
        category="Payment",
        explanation="Pay us",
    )
    assert clause.category == "Payment"
    assert clause.review_priority == "LOW"  # Default
    assert clause.title == ""

"""LegalLens AI — Tests for API routes."""

from unittest.mock import patch

from app.models.document import Document
from app.services.document_service import document_store


def test_health_check(client):
    """Test health endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json["success"] is True


def test_upload_no_file(client):
    """Test upload without file."""
    resp = client.post("/api/documents/upload")
    assert resp.status_code == 422
    assert resp.json["error"]["code"] == "VALIDATION_ERROR"


def test_upload_success(client, sample_file):
    """Test successful document upload."""
    resp = client.post(
        "/api/documents/upload", data={"file": sample_file}, content_type="multipart/form-data"
    )
    assert resp.status_code == 201
    assert resp.json["success"] is True
    assert "id" in resp.json["data"]


def test_get_document(client):
    """Test getting a document."""
    # Seed a document
    doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="hash")
    document_store.add(doc)

    resp = client.get("/api/documents/123")
    assert resp.status_code == 200
    assert resp.json["data"]["id"] == "123"

    resp = client.get("/api/documents/999")
    assert resp.status_code == 404


def test_qa_endpoint(client):
    """Test Q&A endpoint."""
    doc = Document(id="123", filename="test.txt", file_type="txt", file_hash="hash")
    document_store.add(doc)

    # Missing question
    resp = client.post("/api/documents/123/ask", json={})
    assert resp.status_code == 422

    # Valid question (with mocked AI)
    with patch("app.routes.qa.ask_question") as mock_ask:
        from app.models.analysis import QAResponse

        mock_ask.return_value = QAResponse(question="test?", answer="test answer", citations=[])

        resp = client.post("/api/documents/123/ask", json={"question": "test?"})
        assert resp.status_code == 200
        assert resp.json["data"]["answer"] == "test answer"


def test_compare_endpoint(client):
    """Test comparison endpoint."""
    doc1 = Document(id="1", filename="a.txt", file_type="txt", file_hash="h1")
    doc2 = Document(id="2", filename="b.txt", file_type="txt", file_hash="h2")
    document_store.add(doc1)
    document_store.add(doc2)

    # Same document
    resp = client.post("/api/documents/compare", json={"document_a_id": "1", "document_b_id": "1"})
    assert resp.status_code == 422

    # Valid comparison (with mocked AI)
    with patch("app.routes.comparison.compare_documents") as mock_compare:
        from app.models.analysis import ComparisonResult

        mock_compare.return_value = ComparisonResult(document_a_name="a", document_b_name="b")

        resp = client.post(
            "/api/documents/compare", json={"document_a_id": "1", "document_b_id": "2"}
        )
        assert resp.status_code == 200
        assert resp.json["success"] is True

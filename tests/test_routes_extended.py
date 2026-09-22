"""LegalLens AI — Extended API route tests covering more paths."""

from __future__ import annotations

from unittest.mock import patch

from app.models.document import Document
from app.services.document_service import document_store


def _seed_doc(doc_id: str = "test-123", filename: str = "test.txt") -> Document:
    doc = Document(
        id=doc_id,
        filename=filename,
        file_type="txt",
        file_hash=f"hash_{doc_id}",
        full_text="This is test legal document content.",
    )
    document_store.add(doc)
    return doc


class TestDocumentRoutes:
    """Extended document route tests."""

    def test_list_documents_empty(self, client):
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json["data"]["documents"] == []

    def test_list_documents_with_items(self, client):
        _seed_doc("doc1")
        _seed_doc("doc2", "second.txt")
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        docs = resp.json["data"]["documents"]
        assert len(docs) == 2

    def test_get_document_text(self, client):
        _seed_doc()
        resp = client.get("/api/documents/test-123/text")
        assert resp.status_code == 200
        assert "text" in resp.json["data"]

    def test_get_nonexistent_document_text(self, client):
        resp = client.get("/api/documents/nonexistent/text")
        assert resp.status_code == 404

    def test_delete_document(self, client):
        _seed_doc()
        resp = client.delete("/api/documents/test-123")
        assert resp.status_code == 200
        assert resp.json["success"] is True
        # Verify gone
        resp2 = client.get("/api/documents/test-123")
        assert resp2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/documents/nonexistent")
        assert resp.status_code == 404

    def test_upload_wrong_content_type(self, client):
        """Sending JSON instead of form data for upload."""
        resp = client.post("/api/documents/upload", json={"filename": "test.txt"})
        assert resp.status_code == 422

    def test_upload_empty_filename(self, client):
        import io

        resp = client.post(
            "/api/documents/upload",
            data={"file": (io.BytesIO(b"content"), "")},
            content_type="multipart/form-data",
        )
        assert resp.status_code in (422, 400, 500)


class TestAnalysisRoutes:
    """Tests for analysis API routes."""

    def test_summary_nonexistent_doc(self, client):
        resp = client.get("/api/documents/nonexistent/summary")
        assert resp.status_code == 404

    def test_clauses_nonexistent_doc(self, client):
        resp = client.get("/api/documents/nonexistent/clauses")
        assert resp.status_code == 404

    def test_risks_nonexistent_doc(self, client):
        resp = client.get("/api/documents/nonexistent/risks")
        assert resp.status_code == 404

    def test_checklist_nonexistent_doc(self, client):
        resp = client.get("/api/documents/nonexistent/checklist")
        assert resp.status_code == 404

    def test_lawyer_questions_nonexistent_doc(self, client):
        resp = client.get("/api/documents/nonexistent/lawyer-questions")
        assert resp.status_code == 404

    def test_summary_with_mock_ai(self, client):
        _seed_doc()
        with patch("app.routes.analysis.generate_summary") as mock:
            from app.models.analysis import DocumentSummary

            mock.return_value = DocumentSummary(
                quick_summary="A test document",
                key_points=["Point 1"],
            )
            resp = client.get("/api/documents/test-123/summary")
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert resp.json["data"]["quick_summary"] == "A test document"

    def test_clauses_with_mock_ai(self, client):
        _seed_doc()
        with patch("app.routes.analysis.extract_clauses") as mock:
            from app.models.analysis import Clause

            mock.return_value = [Clause(category="Payment", explanation="Pay monthly")]
            resp = client.get("/api/documents/test-123/clauses")
        assert resp.status_code == 200
        assert len(resp.json["data"]["clauses"]) == 1

    def test_risks_with_mock_ai(self, client):
        _seed_doc()
        with patch("app.routes.analysis.analyze_risks") as mock:
            mock.return_value = ([], [])
            resp = client.get("/api/documents/test-123/risks")
        assert resp.status_code == 200
        assert resp.json["data"]["review_flags"] == []

    def test_checklist_with_mock_ai(self, client):
        _seed_doc()
        with patch("app.routes.analysis.generate_checklist") as mock:
            from app.models.analysis import ChecklistItem

            mock.return_value = [ChecklistItem(action="Sign the document")]
            resp = client.get("/api/documents/test-123/checklist")
        assert resp.status_code == 200
        assert len(resp.json["data"]["checklist"]) == 1

    def test_lawyer_questions_with_mock_ai(self, client):
        _seed_doc()
        with patch("app.routes.analysis.generate_lawyer_questions") as mock:
            from app.models.analysis import LawyerQuestion

            mock.return_value = [LawyerQuestion(question="What does this mean?")]
            resp = client.get("/api/documents/test-123/lawyer-questions")
        assert resp.status_code == 200
        assert len(resp.json["data"]["questions"]) == 1


class TestQARoutes:
    """Extended Q&A route tests."""

    def test_ask_nonexistent_doc(self, client):
        resp = client.post(
            "/api/documents/nonexistent/ask", json={"question": "What is the notice period?"}
        )
        assert resp.status_code == 404

    def test_ask_missing_body(self, client):
        _seed_doc()
        resp = client.post("/api/documents/test-123/ask")
        assert resp.status_code in (400, 415, 422)

    def test_ask_empty_question(self, client):
        _seed_doc()
        resp = client.post("/api/documents/test-123/ask", json={"question": "   "})
        assert resp.status_code == 422


class TestComparisonRoutes:
    """Extended comparison route tests."""

    def test_compare_missing_body(self, client):
        resp = client.post("/api/documents/compare")
        assert resp.status_code in (400, 415, 422)

    def test_compare_missing_one_id(self, client):
        resp = client.post("/api/documents/compare", json={"document_a_id": "123"})
        assert resp.status_code == 422

    def test_compare_nonexistent_doc_a(self, client):
        _seed_doc("doc-b")
        resp = client.post(
            "/api/documents/compare",
            json={"document_a_id": "nonexistent", "document_b_id": "doc-b"},
        )
        assert resp.status_code == 404

    def test_compare_nonexistent_doc_b(self, client):
        _seed_doc("doc-a")
        resp = client.post(
            "/api/documents/compare",
            json={"document_a_id": "doc-a", "document_b_id": "nonexistent"},
        )
        assert resp.status_code == 404


class TestErrorHandlerRoutes:
    """Tests for various error handler behaviors."""

    def test_405_method_not_allowed(self, client):
        # DELETE on documents list (only GET/POST allowed)
        resp = client.delete("/api/documents")
        assert resp.status_code in (404, 405)
        assert resp.json["success"] is False

    def test_404_unknown_route(self, client):
        resp = client.get("/api/nonexistent/route/that/does/not/exist")
        # Should return HTML (SPA fallback) or 404
        assert resp.status_code in (200, 404)

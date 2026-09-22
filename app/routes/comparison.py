"""LegalLens AI — Document comparison routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.ai.client import AIClient
from app.models.responses import APIResponse
from app.services.comparison_service import compare_documents
from app.services.document_service import document_store
from app.utils.validators import ValidationError

bp = Blueprint("comparison", __name__, url_prefix="/api/documents")


@bp.route("/compare", methods=["POST"])
def compare() -> tuple:
    """Compare two documents."""
    data = request.get_json()
    if not data or "document_a_id" not in data or "document_b_id" not in data:
        raise ValidationError(
            "VALIDATION_ERROR", "Both 'document_a_id' and 'document_b_id' are required"
        )

    doc_a_id = data["document_a_id"]
    doc_b_id = data["document_b_id"]

    if doc_a_id == doc_b_id:
        raise ValidationError("VALIDATION_ERROR", "Cannot compare a document to itself")

    doc_a = document_store.get(doc_a_id)
    if not doc_a:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document A ({doc_a_id}) not found")

    doc_b = document_store.get(doc_b_id)
    if not doc_b:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document B ({doc_b_id}) not found")

    ai_client = AIClient(
        api_key=current_app.config["GOOGLE_API_KEY"],
        model_name=current_app.config["AI_MODEL_NAME"],
        max_retries=current_app.config["AI_MAX_RETRIES"],
        timeout_seconds=current_app.config["AI_TIMEOUT_SECONDS"],
    )

    result = compare_documents(doc_a, doc_b, ai_client)

    return jsonify(APIResponse.ok(data=result.model_dump()).model_dump()), 200

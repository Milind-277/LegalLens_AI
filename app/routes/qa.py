"""LegalLens AI — Q&A routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.ai.client import AIClient, AIClientError
from app.models.responses import APIResponse
from app.services.document_service import document_store
from app.services.fallback_service import fallback_qa
from app.services.qa_service import ask_question
from app.utils.validators import ValidationError

bp = Blueprint("qa", __name__, url_prefix="/api/documents/<doc_id>")


@bp.route("/ask", methods=["POST"])
def ask_document_question(doc_id: str) -> tuple:
    """Ask a question about a document."""
    doc = document_store.get(doc_id)
    if not doc:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document {doc_id} not found")

    data = request.get_json()
    if not data or "question" not in data:
        raise ValidationError("VALIDATION_ERROR", "Missing 'question' in request body")

    question = data["question"]

    ai_client = AIClient(
        api_key=current_app.config["GOOGLE_API_KEY"],
        model_name=current_app.config["AI_MODEL_NAME"],
        max_retries=current_app.config["AI_MAX_RETRIES"],
        timeout_seconds=current_app.config["AI_TIMEOUT_SECONDS"],
    )

    try:
        response = ask_question(
            doc=doc,
            question=question,
            ai_client=ai_client,
            max_context_chunks=current_app.config["AI_MAX_CONTEXT_CHUNKS"],
        )
        ai_available = True
    except AIClientError:
        response = fallback_qa(doc, question)
        ai_available = False

    payload = response.model_dump()
    payload["ai_available"] = ai_available
    return (
        jsonify(
            APIResponse.ok(
                data=payload,
                ai_available=ai_available,
                analysis_mode="ai" if ai_available else "fallback",
            ).model_dump()
        ),
        200,
    )

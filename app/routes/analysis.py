"""LegalLens AI — Analysis routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from app.ai.client import AIClient
from app.models.responses import APIResponse
from app.services.analysis_service import (
    analyze_risks,
    extract_clauses,
    generate_checklist,
    generate_lawyer_questions,
    generate_summary,
)
from app.services.document_service import document_store
from app.utils.validators import ValidationError

bp = Blueprint("analysis", __name__, url_prefix="/api/documents/<doc_id>")


def _get_ai_client() -> AIClient:
    """Factory for AIClient."""
    return AIClient(
        api_key=current_app.config["GOOGLE_API_KEY"],
        model_name=current_app.config["AI_MODEL_NAME"],
        max_retries=current_app.config["AI_MAX_RETRIES"],
        timeout_seconds=current_app.config["AI_TIMEOUT_SECONDS"],
    )


def _get_document(doc_id: str):
    """Helper to get document or raise error."""
    doc = document_store.get(doc_id)
    if not doc:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document {doc_id} not found")
    return doc


@bp.route("/summary", methods=["GET"])
def get_summary(doc_id: str) -> tuple:
    """Get document summary."""
    doc = _get_document(doc_id)
    ai_client = _get_ai_client()
    summary = generate_summary(doc, ai_client)
    return jsonify(APIResponse.ok(data=summary.model_dump()).model_dump()), 200


@bp.route("/clauses", methods=["GET"])
def get_clauses(doc_id: str) -> tuple:
    """Get document clauses."""
    doc = _get_document(doc_id)
    ai_client = _get_ai_client()
    clauses = extract_clauses(doc, ai_client)
    data = {"clauses": [c.model_dump() for c in clauses]}
    return jsonify(APIResponse.ok(data=data).model_dump()), 200


@bp.route("/risks", methods=["GET"])
def get_risks(doc_id: str) -> tuple:
    """Get document review flags and obligations."""
    doc = _get_document(doc_id)
    ai_client = _get_ai_client()
    flags, obligations = analyze_risks(doc, ai_client)
    data = {
        "review_flags": [f.model_dump() for f in flags],
        "obligations": [o.model_dump() for o in obligations],
    }
    return jsonify(APIResponse.ok(data=data).model_dump()), 200


@bp.route("/checklist", methods=["GET"])
def get_checklist(doc_id: str) -> tuple:
    """Get document action checklist."""
    doc = _get_document(doc_id)
    ai_client = _get_ai_client()
    checklist = generate_checklist(doc, ai_client)
    data = {"checklist": [i.model_dump() for i in checklist]}
    return jsonify(APIResponse.ok(data=data).model_dump()), 200


@bp.route("/lawyer-questions", methods=["GET"])
def get_lawyer_questions(doc_id: str) -> tuple:
    """Get prepared lawyer questions."""
    doc = _get_document(doc_id)
    ai_client = _get_ai_client()
    questions = generate_lawyer_questions(doc, ai_client)
    data = {"questions": [q.model_dump() for q in questions]}
    return jsonify(APIResponse.ok(data=data).model_dump()), 200

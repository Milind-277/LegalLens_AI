"""LegalLens AI — Document routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.models.responses import APIResponse
from app.services.analysis_service import clear_analysis_cache
from app.services.document_service import document_store, process_upload
from app.utils.validators import ValidationError

bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@bp.route("/upload", methods=["POST"])
def upload_document() -> tuple:
    """Upload and process a document."""
    if "file" not in request.files:
        raise ValidationError("VALIDATION_ERROR", "No file provided in the request")

    file = request.files["file"]
    if not file.filename:
        raise ValidationError("VALIDATION_ERROR", "Empty filename")

    filename = secure_filename(file.filename)
    file_bytes = file.read()

    # Process the file
    doc = process_upload(
        file_bytes=file_bytes,
        filename=filename,
        max_size_bytes=current_app.config["MAX_CONTENT_LENGTH"],
    )

    return jsonify(APIResponse.ok(data=doc.to_summary_dict()).model_dump()), 201


@bp.route("/demo", methods=["POST"])
def load_demo_document() -> tuple:
    """Load the built-in demo document for demonstration purposes."""
    from app.services.demo_service import (
        DEMO_DOCUMENT_FILENAME,
        DEMO_DOCUMENT_TEXT,
    )

    # Check if demo doc is already loaded
    for doc in document_store._documents.values():
        if "DEMO" in doc.filename:
            return jsonify(APIResponse.ok(data=doc.to_summary_dict()).model_dump()), 200

    demo_bytes = DEMO_DOCUMENT_TEXT.encode("utf-8")
    doc = process_upload(
        file_bytes=demo_bytes,
        filename=DEMO_DOCUMENT_FILENAME,
        max_size_bytes=current_app.config["MAX_CONTENT_LENGTH"],
    )

    return jsonify(APIResponse.ok(data=doc.to_summary_dict()).model_dump()), 201


@bp.route("", methods=["GET"])
def list_documents() -> tuple:
    """List all uploaded documents."""
    docs = document_store.list_all()
    return jsonify(APIResponse.ok(data={"documents": docs}).model_dump()), 200


@bp.route("/<doc_id>", methods=["GET"])
def get_document(doc_id: str) -> tuple:
    """Get document metadata."""
    doc = document_store.get(doc_id)
    if not doc:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document {doc_id} not found")

    return jsonify(APIResponse.ok(data=doc.to_summary_dict()).model_dump()), 200


@bp.route("/<doc_id>/text", methods=["GET"])
def get_document_text(doc_id: str) -> tuple:
    """Get document full text."""
    doc = document_store.get(doc_id)
    if not doc:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document {doc_id} not found")

    return (
        jsonify(
            APIResponse.ok(
                data={"id": doc.id, "filename": doc.filename, "text": doc.full_text}
            ).model_dump()
        ),
        200,
    )


@bp.route("/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str) -> tuple:
    """Delete a document and its analysis cache."""
    doc = document_store.get(doc_id)
    if not doc:
        raise ValidationError("DOCUMENT_NOT_FOUND", f"Document {doc_id} not found")

    document_store.delete(doc_id)
    clear_analysis_cache(doc_id)

    return jsonify(APIResponse.ok(message="Document deleted successfully").model_dump()), 200

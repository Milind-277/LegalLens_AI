"""LegalLens AI — Document analysis service."""

from __future__ import annotations

import structlog

from app.ai.client import AIClient, AIClientError
from app.ai.parser import (
    parse_checklist_response,
    parse_clauses_response,
    parse_lawyer_questions_response,
    parse_risk_response,
    parse_summary_response,
)
from app.ai.prompts import (
    build_checklist_prompt,
    build_clause_prompt,
    build_lawyer_questions_prompt,
    build_risk_prompt,
    build_summary_prompt,
)
from app.ai.safety import get_legal_disclaimer
from app.models.analysis import (
    ChecklistItem,
    Clause,
    DocumentAnalysis,
    DocumentSummary,
    LawyerQuestion,
    Obligation,
    ReviewFlag,
)
from app.models.document import Document

logger = structlog.get_logger(__name__)


# In-memory cache for analysis results
_analysis_cache: dict[str, DocumentAnalysis] = {}


def get_or_create_analysis(doc: Document, ai_client: AIClient) -> DocumentAnalysis:
    """Get cached analysis or create a new one."""
    if doc.id in _analysis_cache:
        return _analysis_cache[doc.id]

    analysis = DocumentAnalysis(
        document_id=doc.id,
        disclaimer=get_legal_disclaimer(),
    )
    _analysis_cache[doc.id] = analysis
    return analysis


def generate_summary(doc: Document, ai_client: AIClient) -> DocumentSummary:
    """Generate multi-level document summary."""
    analysis = get_or_create_analysis(doc, ai_client)

    # Return cached if available
    if analysis.summary.quick_summary:
        return analysis.summary

    system, prompt = build_summary_prompt(doc.full_text)

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        summary = parse_summary_response(raw)
        analysis.summary = summary
        logger.info("summary_generated", doc_id=doc.id)
        return summary
    except AIClientError as exc:
        logger.error("summary_generation_failed", doc_id=doc.id, error=str(exc))
        raise


def extract_clauses(doc: Document, ai_client: AIClient) -> list[Clause]:
    """Extract key clauses from document."""
    analysis = get_or_create_analysis(doc, ai_client)

    if analysis.clauses:
        return analysis.clauses

    system, prompt = build_clause_prompt(doc.full_text)

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        clauses = parse_clauses_response(raw)
        analysis.clauses = clauses
        logger.info("clauses_extracted", doc_id=doc.id, count=len(clauses))
        return clauses
    except AIClientError as exc:
        logger.error("clause_extraction_failed", doc_id=doc.id, error=str(exc))
        raise


def analyze_risks(doc: Document, ai_client: AIClient) -> tuple[list[ReviewFlag], list[Obligation]]:
    """Analyze document for review flags and obligations."""
    analysis = get_or_create_analysis(doc, ai_client)

    if analysis.review_flags or analysis.obligations:
        return analysis.review_flags, analysis.obligations

    system, prompt = build_risk_prompt(doc.full_text)

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        flags, obligations = parse_risk_response(raw)
        analysis.review_flags = flags
        analysis.obligations = obligations
        logger.info(
            "risk_analysis_completed",
            doc_id=doc.id,
            flags=len(flags),
            obligations=len(obligations),
        )
        return flags, obligations
    except AIClientError as exc:
        logger.error("risk_analysis_failed", doc_id=doc.id, error=str(exc))
        raise


def generate_checklist(doc: Document, ai_client: AIClient) -> list[ChecklistItem]:
    """Generate action checklist from document."""
    analysis = get_or_create_analysis(doc, ai_client)

    if analysis.checklist:
        return analysis.checklist

    system, prompt = build_checklist_prompt(doc.full_text)

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        checklist = parse_checklist_response(raw)
        analysis.checklist = checklist
        logger.info("checklist_generated", doc_id=doc.id, items=len(checklist))
        return checklist
    except AIClientError as exc:
        logger.error("checklist_generation_failed", doc_id=doc.id, error=str(exc))
        raise


def generate_lawyer_questions(doc: Document, ai_client: AIClient) -> list[LawyerQuestion]:
    """Generate questions for a legal professional."""
    analysis = get_or_create_analysis(doc, ai_client)

    if analysis.lawyer_questions:
        return analysis.lawyer_questions

    system, prompt = build_lawyer_questions_prompt(doc.full_text)

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        questions = parse_lawyer_questions_response(raw)
        analysis.lawyer_questions = questions
        logger.info("lawyer_questions_generated", doc_id=doc.id, count=len(questions))
        return questions
    except AIClientError as exc:
        logger.error("lawyer_questions_failed", doc_id=doc.id, error=str(exc))
        raise


def clear_analysis_cache(doc_id: str | None = None) -> None:
    """Clear analysis cache for a document or all documents."""
    if doc_id:
        _analysis_cache.pop(doc_id, None)
    else:
        _analysis_cache.clear()

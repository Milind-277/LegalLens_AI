"""LegalLens AI — AI response parser with Pydantic validation."""

from __future__ import annotations

from typing import Any

import structlog

from app.ai.client import parse_json_response
from app.models.analysis import (
    ChecklistItem,
    Citation,
    Clause,
    ComparisonItem,
    ComparisonResult,
    DocumentSummary,
    LawyerQuestion,
    Obligation,
    QAResponse,
    ReviewFlag,
)

logger = structlog.get_logger(__name__)


def parse_summary_response(raw: str) -> DocumentSummary:
    """Parse AI response into DocumentSummary."""
    data = parse_json_response(raw)
    return DocumentSummary(
        quick_summary=_get_str(data, "quick_summary"),
        detailed_summary=_get_str(data, "detailed_summary"),
        executive_summary=_get_str(data, "executive_summary"),
        key_points=_get_list(data, "key_points"),
        parties=_get_list(data, "parties"),
        document_type=_get_str(data, "document_type", "Unknown"),
        effective_date=data.get("effective_date"),
        key_dates=_get_list(data, "key_dates"),
    )


def parse_clauses_response(raw: str) -> list[Clause]:
    """Parse AI response into list of Clause models."""
    data = parse_json_response(raw)
    clauses_data = data.get("clauses", [])

    if not isinstance(clauses_data, list):
        logger.warning("clauses_not_list", type=type(clauses_data).__name__)
        return []

    clauses: list[Clause] = []
    for item in clauses_data:
        if not isinstance(item, dict):
            continue
        try:
            clauses.append(
                Clause(
                    category=_get_str(item, "category", "Other"),
                    title=_get_str(item, "title"),
                    explanation=_get_str(item, "explanation"),
                    original_text=_get_str(item, "original_text"),
                    citation=_parse_citation(item),
                    review_priority=_get_priority(item),
                )
            )
        except Exception:
            logger.warning("clause_parse_skipped", item_preview=str(item)[:100])
            continue

    return clauses


def parse_risk_response(raw: str) -> tuple[list[ReviewFlag], list[Obligation]]:
    """Parse AI response into review flags and obligations."""
    data = parse_json_response(raw)

    flags: list[ReviewFlag] = []
    for item in data.get("review_flags", []):
        if not isinstance(item, dict):
            continue
        try:
            flags.append(
                ReviewFlag(
                    title=_get_str(item, "title"),
                    explanation=_get_str(item, "explanation"),
                    evidence=_get_str(item, "evidence"),
                    citation=_parse_citation(item),
                    review_priority=_get_priority(item),
                    suggested_action=_get_str(item, "suggested_action"),
                )
            )
        except Exception:
            logger.warning("flag_parse_skipped", item_preview=str(item)[:100])

    obligations: list[Obligation] = []
    for item in data.get("obligations", []):
        if not isinstance(item, dict):
            continue
        try:
            obligations.append(
                Obligation(
                    actor=_get_str(item, "actor"),
                    obligation=_get_str(item, "obligation"),
                    deadline=item.get("deadline"),
                    trigger=item.get("trigger"),
                    citation=_parse_citation(item),
                    review_priority=_get_priority(item),
                )
            )
        except Exception:
            logger.warning("obligation_parse_skipped", item_preview=str(item)[:100])

    return flags, obligations


def parse_qa_response(raw: str, question: str) -> QAResponse:
    """Parse AI response into QAResponse."""
    data = parse_json_response(raw)
    citations = [_parse_citation(c) for c in data.get("citations", []) if isinstance(c, dict)]

    return QAResponse(
        question=question,
        answer=_get_str(data, "answer", "I was unable to process this question."),
        citations=citations,
        grounding_status=_get_str(data, "grounding_status", "partially_grounded"),
        confidence=_get_str(data, "confidence", "low"),
        disclaimer=_get_str(data, "disclaimer"),
    )


def parse_comparison_response(raw: str, doc_a_name: str, doc_b_name: str) -> ComparisonResult:
    """Parse AI response into ComparisonResult."""
    data = parse_json_response(raw)

    items: list[ComparisonItem] = []
    for item in data.get("items", []):
        if not isinstance(item, dict):
            continue
        try:
            items.append(
                ComparisonItem(
                    category=_get_str(item, "category"),
                    document_a=_get_str(item, "document_a"),
                    document_b=_get_str(item, "document_b"),
                    status=_get_str(item, "status", "unchanged"),
                    explanation=_get_str(item, "explanation"),
                )
            )
        except Exception:
            logger.warning("comparison_item_skipped", item_preview=str(item)[:100])

    return ComparisonResult(
        document_a_name=doc_a_name,
        document_b_name=doc_b_name,
        items=items,
        summary=_get_str(data, "summary"),
        key_differences=_get_list(data, "key_differences"),
    )


def parse_checklist_response(raw: str) -> list[ChecklistItem]:
    """Parse AI response into checklist items."""
    data = parse_json_response(raw)

    items: list[ChecklistItem] = []
    for item in data.get("checklist", []):
        if not isinstance(item, dict):
            continue
        try:
            items.append(
                ChecklistItem(
                    action=_get_str(item, "action"),
                    responsible_party=_get_str(item, "responsible_party"),
                    deadline=item.get("deadline"),
                    priority=_get_priority(item),
                    source=_get_str(item, "source"),
                )
            )
        except Exception:
            logger.warning("checklist_item_skipped", item_preview=str(item)[:100])

    return items


def parse_lawyer_questions_response(raw: str) -> list[LawyerQuestion]:
    """Parse AI response into lawyer questions."""
    data = parse_json_response(raw)

    questions: list[LawyerQuestion] = []
    for item in data.get("questions", []):
        if not isinstance(item, dict):
            continue
        try:
            questions.append(
                LawyerQuestion(
                    question=_get_str(item, "question"),
                    context=_get_str(item, "context"),
                    related_clause=_get_str(item, "related_clause"),
                    priority=_get_priority(item),
                )
            )
        except Exception:
            logger.warning("question_parse_skipped", item_preview=str(item)[:100])

    return questions


# --- Helpers ---


def _get_str(data: dict[str, Any], key: str, default: str = "") -> str:
    """Safely extract a string value."""
    val = data.get(key, default)
    if val is None:
        return default
    return str(val)


def _get_list(data: dict[str, Any], key: str) -> list[str]:
    """Safely extract a list of strings."""
    val = data.get(key, [])
    if not isinstance(val, list):
        return []
    return [str(item) for item in val if item is not None]


def _get_priority(data: dict[str, Any]) -> str:
    """Extract and validate review priority."""
    val = _get_str(data, "review_priority", "MEDIUM").upper()
    valid = {"LOW", "MEDIUM", "HIGH", "REVIEW"}
    return val if val in valid else "MEDIUM"


def _parse_citation(data: dict[str, Any]) -> Citation:
    """Parse citation from a data dict that may have page/section/text fields."""
    return Citation(
        page=data.get("page"),
        section=data.get("section"),
        text=_get_str(data, "text")
        or _get_str(data, "evidence")
        or _get_str(data, "original_text"),
    )

"""LegalLens AI — Grounding and citation validation."""

from __future__ import annotations

import structlog

from app.models.analysis import Citation, QAResponse

logger = structlog.get_logger(__name__)


def validate_citations(
    response: QAResponse,
    document_text: str,
) -> QAResponse:
    """Validate that citations in the response actually exist in the document.

    Updates grounding_status if citations cannot be verified.
    """
    if not response.citations:
        # No citations — if answer claims to be grounded, downgrade
        if response.grounding_status == "grounded" and response.answer:
            response.grounding_status = "partially_grounded"
        return response

    verified_citations: list[Citation] = []
    for citation in response.citations:
        if citation.text and _text_exists_in_document(citation.text, document_text):
            verified_citations.append(citation)
        else:
            logger.info(
                "citation_not_verified",
                text_preview=citation.text[:80] if citation.text else "empty",
            )

    response.citations = verified_citations

    # Update grounding status based on verification
    if not verified_citations and response.grounding_status == "grounded":
        response.grounding_status = "partially_grounded"

    return response


def _text_exists_in_document(citation_text: str, document_text: str) -> bool:
    """Check if citation text can be found (approximately) in the document."""
    if not citation_text or not document_text:
        return False

    # Normalize for comparison
    norm_citation = _normalize_for_comparison(citation_text)
    norm_doc = _normalize_for_comparison(document_text)

    # Direct substring check
    if norm_citation in norm_doc:
        return True

    # Check if enough words overlap (fuzzy matching for paraphrased citations)
    citation_words = set(norm_citation.split())
    doc_words = set(norm_doc.split())

    if not citation_words:
        return False

    overlap = len(citation_words & doc_words)
    overlap_ratio = overlap / len(citation_words)

    # Require a high overlap ratio to prevent hallucinated numbers from passing
    return overlap_ratio >= 0.85


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for fuzzy comparison."""
    return " ".join(text.lower().split())


def check_grounding_quality(answer: str, document_text: str) -> str:
    """Determine how well an answer is grounded in the document.

    Returns grounding status: grounded, partially_grounded, not_found, general_info.
    """
    if not answer or not document_text:
        return "not_found"

    norm_answer = _normalize_for_comparison(answer)
    norm_doc = _normalize_for_comparison(document_text)

    # Check for "not found" indicators
    not_found_phrases = [
        "could not find",
        "couldn't find",
        "not found in",
        "does not mention",
        "doesn't mention",
        "no information",
        "not specified in the document",
        "not in the provided document",
        "does not contain",
    ]
    for phrase in not_found_phrases:
        if phrase in norm_answer:
            return "not_found"

    # Check for advice redirection indicators
    advice_phrases = [
        "consult with a",
        "speak with a",
        "legal professional",
        "qualified attorney",
        "seek legal advice",
    ]
    for phrase in advice_phrases:
        if phrase in norm_answer:
            return "general_info"

    # Check word overlap between answer and document
    answer_words = set(norm_answer.split()) - _COMMON_WORDS
    doc_words = set(norm_doc.split())

    if not answer_words:
        return "partially_grounded"

    overlap = len(answer_words & doc_words)
    ratio = overlap / len(answer_words)

    if ratio >= 0.4:
        return "grounded"
    elif ratio >= 0.2:
        return "partially_grounded"
    else:
        return "general_info"


_COMMON_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "and",
        "or",
        "but",
        "if",
        "this",
        "that",
        "these",
        "those",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "it",
        "its",
        "not",
        "no",
    }
)

"""LegalLens AI — Document comparison service."""

from __future__ import annotations

import structlog

from app.ai.client import AIClient, AIClientError
from app.ai.parser import parse_comparison_response
from app.ai.prompts import build_comparison_prompt
from app.models.analysis import ComparisonResult
from app.models.document import Document

logger = structlog.get_logger(__name__)

# Cache comparison results
_comparison_cache: dict[str, ComparisonResult] = {}


def compare_documents(
    doc_a: Document,
    doc_b: Document,
    ai_client: AIClient,
) -> ComparisonResult:
    """Compare two documents and identify differences.

    Uses representative chunks from each document to stay within context limits.

    Args:
        doc_a: First document.
        doc_b: Second document.
        ai_client: AI client for generation.

    Returns:
        ComparisonResult with itemized differences.
    """
    cache_key = f"{doc_a.id}:{doc_b.id}"
    if cache_key in _comparison_cache:
        return _comparison_cache[cache_key]

    # Use full text but limit size for each document
    max_chars_per_doc = 6000
    text_a = doc_a.full_text[:max_chars_per_doc]
    text_b = doc_b.full_text[:max_chars_per_doc]

    system, prompt = build_comparison_prompt(
        doc_a_text=text_a,
        doc_b_text=text_b,
        doc_a_name=doc_a.filename,
        doc_b_name=doc_b.filename,
    )

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        result = parse_comparison_response(raw, doc_a.filename, doc_b.filename)

        _comparison_cache[cache_key] = result
        logger.info(
            "comparison_completed",
            doc_a=doc_a.id,
            doc_b=doc_b.id,
            items=len(result.items),
        )
        return result

    except AIClientError as exc:
        logger.error("comparison_failed", doc_a=doc_a.id, doc_b=doc_b.id, error=str(exc))
        raise


def clear_comparison_cache() -> None:
    """Clear comparison cache."""
    _comparison_cache.clear()

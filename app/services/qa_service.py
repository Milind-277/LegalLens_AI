"""LegalLens AI — Document Q&A service."""

from __future__ import annotations

import structlog

from app.ai.client import AIClient, AIClientError
from app.ai.grounding import validate_citations
from app.ai.parser import parse_qa_response
from app.ai.prompts import build_qa_prompt
from app.ai.retrieval import assemble_context, retrieve_relevant_chunks
from app.ai.safety import get_advice_disclaimer, sanitize_ai_response
from app.models.analysis import QAResponse
from app.models.document import Document
from app.utils.validators import validate_question

logger = structlog.get_logger(__name__)


def ask_question(
    doc: Document,
    question: str,
    ai_client: AIClient,
    max_context_chunks: int = 10,
) -> QAResponse:
    """Answer a question about a document using RAG-style retrieval.

    Pipeline:
    1. Validate question
    2. Retrieve relevant chunks
    3. Assemble context
    4. Generate answer with LLM
    5. Parse and validate response
    6. Validate citations
    7. Apply safety checks
    8. Return grounded response

    Args:
        doc: The document to query.
        question: User's question.
        ai_client: AI client for generation.
        max_context_chunks: Max chunks to include in context.

    Returns:
        QAResponse with answer, citations, and grounding status.
    """
    question = validate_question(question)

    # Check for legal advice requests
    advice_disclaimer = get_advice_disclaimer(question)

    # Retrieve relevant chunks
    relevant_chunks = retrieve_relevant_chunks(
        query=question,
        chunks=doc.chunks,
        top_k=max_context_chunks,
    )

    if not relevant_chunks:
        logger.info("no_relevant_chunks", doc_id=doc.id, question=question[:50])
        return QAResponse(
            question=question,
            answer="I couldn't find relevant information in the document to answer this question.",
            citations=[],
            grounding_status="not_found",
            confidence="low",
            disclaimer=advice_disclaimer,
        )

    # Assemble context from relevant chunks
    context = assemble_context(relevant_chunks)

    # Build prompt and generate response
    system, prompt = build_qa_prompt(
        question=question,
        relevant_context=context,
        document_name=doc.filename,
    )

    try:
        raw = ai_client.generate(prompt, system_instruction=system)
        raw = sanitize_ai_response(raw)
        response = parse_qa_response(raw, question)

        # Validate citations against actual document
        response = validate_citations(response, doc.full_text)

        # Add advice disclaimer if needed
        if advice_disclaimer and not response.disclaimer:
            response.disclaimer = advice_disclaimer

        logger.info(
            "qa_completed",
            doc_id=doc.id,
            grounding=response.grounding_status,
            citations=len(response.citations),
        )

        return response

    except AIClientError as exc:
        logger.error("qa_failed", doc_id=doc.id, error=str(exc))
        raise

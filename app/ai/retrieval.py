"""LegalLens AI — Lightweight document retrieval for RAG/grounding."""

from __future__ import annotations

import math
import re
from collections import Counter

import structlog

from app.models.document import DocumentChunk

logger = structlog.get_logger(__name__)


def retrieve_relevant_chunks(
    query: str,
    chunks: list[DocumentChunk],
    top_k: int = 10,
) -> list[DocumentChunk]:
    """Retrieve the most relevant chunks for a query using TF-IDF-like scoring.

    This is a deterministic, dependency-free retrieval strategy that avoids
    the need for external vector databases or embedding models.

    Args:
        query: User's question or search query.
        chunks: All document chunks.
        top_k: Maximum number of chunks to return.

    Returns:
        List of most relevant chunks, ordered by relevance score.
    """
    if not query or not chunks:
        return []

    if len(chunks) <= top_k:
        return chunks

    query_terms = _tokenize(query)
    if not query_terms:
        return chunks[:top_k]

    # Build document frequency
    doc_freq: Counter[str] = Counter()
    for chunk in chunks:
        chunk_terms = set(_tokenize(chunk.text))
        for term in chunk_terms:
            doc_freq[term] += 1

    num_docs = len(chunks)

    # Score each chunk
    scored: list[tuple[float, int, DocumentChunk]] = []
    for idx, chunk in enumerate(chunks):
        score = _score_chunk(chunk.text, query_terms, doc_freq, num_docs)
        scored.append((score, idx, chunk))

    # Sort by score descending, then by position for stability
    scored.sort(key=lambda x: (-x[0], x[1]))

    return [chunk for _, _, chunk in scored[:top_k]]


def assemble_context(
    chunks: list[DocumentChunk],
    max_chars: int = 12000,
) -> str:
    """Assemble retrieved chunks into a context string for the LLM.

    Args:
        chunks: Retrieved chunks, ordered by relevance.
        max_chars: Maximum total character count.

    Returns:
        Assembled context string with source markers.
    """
    parts: list[str] = []
    total_chars = 0

    for chunk in chunks:
        # Add source marker
        source_info = []
        if chunk.page:
            source_info.append(f"Page {chunk.page}")
        if chunk.section:
            source_info.append(f"Section: {chunk.section}")

        marker = f"[Source: {', '.join(source_info)}]" if source_info else ""
        entry = f"{marker}\n{chunk.text}" if marker else chunk.text

        if total_chars + len(entry) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 100:
                parts.append(entry[:remaining])
            break

        parts.append(entry)
        total_chars += len(entry) + 2  # +2 for separator

    return "\n\n".join(parts)


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase, split on non-alphanumeric, filter stopwords."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _score_chunk(
    chunk_text: str,
    query_terms: list[str],
    doc_freq: Counter[str],
    num_docs: int,
) -> float:
    """Score a chunk against query terms using TF-IDF-like scoring."""
    chunk_tokens = _tokenize(chunk_text)
    if not chunk_tokens:
        return 0.0

    chunk_tf: Counter[str] = Counter(chunk_tokens)
    chunk_len = len(chunk_tokens)

    score = 0.0
    for term in query_terms:
        tf = chunk_tf.get(term, 0) / chunk_len
        df = doc_freq.get(term, 0)
        idf = math.log(1 + num_docs / (1 + df)) if df > 0 else 0
        score += tf * idf

    return score


# Common English stopwords
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
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
        "need",
        "not",
        "no",
        "nor",
        "so",
        "if",
        "then",
        "than",
        "too",
        "very",
        "just",
        "about",
        "above",
        "after",
        "again",
        "all",
        "also",
        "am",
        "any",
        "because",
        "before",
        "between",
        "both",
        "each",
        "few",
        "he",
        "her",
        "here",
        "him",
        "his",
        "how",
        "it",
        "its",
        "me",
        "more",
        "most",
        "my",
        "new",
        "now",
        "only",
        "other",
        "our",
        "out",
        "own",
        "same",
        "she",
        "some",
        "such",
        "that",
        "their",
        "them",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "up",
        "we",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "you",
        "your",
    }
)

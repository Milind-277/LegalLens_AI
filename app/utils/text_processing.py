"""LegalLens AI — Text processing utilities."""

from __future__ import annotations

import re

from app.models.document import DocumentChunk
from app.utils.constants import CHUNK_OVERLAP, CHUNK_SIZE, MAX_DOCUMENT_CHARS, MIN_DOCUMENT_CHARS


def normalize_text(text: str) -> str:
    """Normalize extracted text: fix encoding issues, normalize whitespace."""
    if not text:
        return ""

    # Replace common encoding artifacts
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple blank lines into at most two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def detect_sections(text: str) -> list[dict[str, int | str]]:
    """Detect section headings and their positions in text.

    Returns list of {heading, start_pos} dicts.
    """
    sections: list[dict[str, int | str]] = []

    # Common legal document section patterns
    patterns = [
        # Numbered sections: "1. DEFINITIONS", "Section 2: Payment"
        r"(?m)^(?:(?:SECTION|Section|section)\s+)?\d+\.?\s+[\w\s&/,\-]{2,}$",
        # Article style: "ARTICLE I", "Article 2"
        r"(?m)^(?:ARTICLE|Article)\s+[IVXLCDM\d]+\.?\s*[-\u2013\u2014:]?\s*\w+.*$",
        # ALL CAPS headings (at least 3 chars, standalone line)
        r"(?m)^[A-Z][A-Z\s&/,\-]{2,}$",
        # Numbered with parentheses: "(a) Definitions"
        r"(?m)^\([a-z]\)\s+[A-Z]\w+.*$",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            heading = match.group().strip()
            if len(heading) > 3 and len(heading) < 100:
                sections.append({"heading": heading, "start_pos": match.start()})

    # Sort by position and deduplicate nearby headings
    sections.sort(key=lambda s: s["start_pos"])
    deduped: list[dict[str, int | str]] = []
    for section in sections:
        if not deduped or abs(int(section["start_pos"]) - int(deduped[-1]["start_pos"])) > 10:
            deduped.append(section)

    return deduped


def get_section_for_position(sections: list[dict[str, int | str]], pos: int) -> str | None:
    """Find which section a character position belongs to."""
    current_section = None
    for section in sections:
        if int(section["start_pos"]) <= pos:
            current_section = str(section["heading"])
        else:
            break
    return current_section


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    page_breaks: list[int] | None = None,
) -> list[DocumentChunk]:
    """Split text into overlapping chunks with metadata.

    Args:
        text: Full document text.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks.
        page_breaks: Character positions where page breaks occur.

    Returns:
        List of DocumentChunk with positional metadata.
    """
    if not text or len(text) < MIN_DOCUMENT_CHARS:
        if text and text.strip():
            return [
                DocumentChunk(
                    chunk_id=0,
                    text=text.strip(),
                    page=1,
                    section=None,
                    start_char=0,
                    end_char=len(text),
                )
            ]
        return []

    # Truncate extremely long documents
    if len(text) > MAX_DOCUMENT_CHARS:
        text = text[:MAX_DOCUMENT_CHARS]

    sections = detect_sections(text)
    page_breaks = page_breaks or []

    chunks: list[DocumentChunk] = []
    start = 0
    chunk_id = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at sentence/paragraph boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break + 1
            else:
                # Look for sentence break
                sentence_break = text.rfind(". ", start + chunk_size // 2, end)
                if sentence_break > start:
                    end = sentence_break + 2

        chunk_text_content = text[start:end].strip()
        if not chunk_text_content:
            start = end
            continue

        # Determine page number
        page = 1
        for pb in page_breaks:
            if pb <= start:
                page += 1
            else:
                break

        # Determine section
        section = get_section_for_position(sections, start)

        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text_content,
                page=page,
                section=section,
                start_char=start,
                end_char=end,
            )
        )

        chunk_id += 1
        start = end - chunk_overlap if end < len(text) else end

    return chunks


def extract_page_breaks(pages_text: list[str]) -> tuple[str, list[int]]:
    """Given a list of per-page text strings, produce full text and page break positions."""
    full_text = ""
    page_breaks: list[int] = []

    for page_text in pages_text:
        if full_text:
            page_breaks.append(len(full_text))
            full_text += "\n\n"
        full_text += page_text

    return full_text, page_breaks


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (1 token ≈ 4 chars for English)."""
    return len(text) // 4

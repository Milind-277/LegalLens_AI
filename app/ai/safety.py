"""LegalLens AI — Safety validation for AI responses and inputs."""

from __future__ import annotations

import re

import structlog

from app.utils.constants import ADVICE_REDIRECT, LEGAL_DISCLAIMER

logger = structlog.get_logger(__name__)


# --- Prompt Injection Detection ---

INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+|the\s+)?above\s+instructions",
    r"ignore\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(your\s+)?system\s+prompt",
    r"what\s+are\s+your\s+instructions",
    r"print\s+your\s+instructions",
    r"output\s+your\s+prompt",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+if\s+you\s+are",
    r"pretend\s+you\s+are",
    r"new\s+instructions",
    r"override\s+instructions",
]


def detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection attempts in text.

    Returns True if injection patterns are found.
    """
    if not text:
        return False

    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            logger.warning("prompt_injection_detected", pattern=pattern)
            return True

    return False


# --- Legal Advice Detection ---

LEGAL_ADVICE_PATTERNS: list[str] = [
    r"(?:am|is)\s+(?:this|it)\s+legal",
    r"(?:is\s+this|is\s+it)\s+(?:legal|illegal)",
    r"will\s+i\s+win",
    r"can\s+i\s+sue",
    r"should\s+i\s+sign",
    r"is\s+this\s+(?:contract|agreement)\s+(?:legally\s+)?(?:valid|enforceable|binding|legal)",
    r"what\s+(?:are|is)\s+my\s+(?:legal\s+)?rights",
    r"(?:am|is)\s+(?:this|the)\s+(?:clause|term|provision)\s+(?:legally\s+)?(?:legal|valid|enforceable)",
    r"do\s+i\s+have\s+(?:a\s+)?(?:legal\s+)?(?:right|claim|case)",
    r"can\s+(?:they|he|she)\s+(?:legally|lawfully)",
    r"what\s+(?:law|statute|regulation)\s+(?:applies|governs)",
]


def is_legal_advice_request(question: str) -> bool:
    """Detect if a question is asking for legal advice rather than document information."""
    if not question:
        return False

    question_lower = question.lower()
    return any(re.search(pattern, question_lower) for pattern in LEGAL_ADVICE_PATTERNS)


def get_advice_disclaimer(question: str) -> str:
    """Get appropriate disclaimer if the question seeks legal advice."""
    if is_legal_advice_request(question):
        return ADVICE_REDIRECT
    return ""


# --- Response Safety ---


def sanitize_ai_response(response_text: str) -> str:
    """Sanitize AI response text for safe display."""
    if not response_text:
        return ""

    # Remove any system prompt leakage patterns
    leakage_patterns = [
        r"(?:system\s+prompt|system\s+instructions?)\s*[:=].*",
        r"(?:my\s+instructions?\s+(?:are|is))\s*[:=].*",
    ]

    for pattern in leakage_patterns:
        response_text = re.sub(pattern, "[content filtered]", response_text, flags=re.IGNORECASE)

    return response_text


def get_legal_disclaimer() -> str:
    """Return the standard legal disclaimer."""
    return LEGAL_DISCLAIMER

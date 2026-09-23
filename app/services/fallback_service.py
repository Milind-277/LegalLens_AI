"""LegalLens AI — Deterministic Fallback Analysis Service.

This module provides AI-free, keyword/regex-based document analysis.
It is used when:
  1. No GOOGLE_API_KEY is configured.
  2. The Gemini API is unavailable or quota-limited.
  3. During testing (no network calls).

Results are document-grounded and clearly labelled as fallback/deterministic.
Nothing is invented — all information comes from the uploaded document text.
"""

from __future__ import annotations

import difflib
import re

from app.ai.retrieval import retrieve_relevant_chunks
from app.ai.safety import get_advice_disclaimer
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
from app.models.document import Document

# ─── Clause keyword map ────────────────────────────────────────────────────────
_CLAUSE_KEYWORDS: dict[str, list[str]] = {
    "Termination": [
        "terminat",
        "cancel",
        "end of agreement",
        "end of contract",
        "at-will",
        "notice of termination",
    ],
    "Confidentiality": [
        "confidential",
        "non-disclosure",
        "nda",
        "proprietary",
        "trade secret",
        "keep secret",
        "not disclose",
    ],
    "Payment & Compensation": [
        "payment",
        "salary",
        "compensation",
        "fee",
        "remuneration",
        "invoice",
        "base salary",
        "bonus",
        "commission",
    ],
    "Intellectual Property": [
        "intellectual property",
        "ip rights",
        "copyright",
        "patent",
        "trademark",
        "work product",
        "invention",
        "assigns",
    ],
    "Liability & Indemnity": [
        "liability",
        "liable",
        "indemnif",
        "indemnity",
        "hold harmless",
        "damages",
        "limitation of liability",
    ],
    "Term / Duration": [
        "term of",
        "duration",
        "effective date",
        "commencement",
        "start date",
        "expir",
        "period of",
    ],
    "Governing Law": [
        "governing law",
        "jurisdiction",
        "governed by the laws",
        "venue",
        "arbitration",
        "dispute resolution",
    ],
    "Non-Compete / Non-Solicitation": [
        "non-compete",
        "non-solicitation",
        "not compete",
        "not solicit",
        "restrictive covenant",
    ],
    "Renewal & Extension": [
        "renew",
        "renewal",
        "auto-renew",
        "automatic renewal",
        "extension",
        "extend",
    ],
    "Warranties & Representations": [
        "warrant",
        "warranty",
        "represent",
        "representation",
        "guarantee",
    ],
    "Privacy & Data": [
        "privacy",
        "personal data",
        "personal information",
        "gdpr",
        "data protection",
        "data processing",
    ],
    "Force Majeure": [
        "force majeure",
        "act of god",
        "circumstances beyond",
        "unforeseeable",
    ],
}

# ─── Obligation trigger words ──────────────────────────────────────────────────
_OBLIGATION_TRIGGERS = ["shall", "must", "agrees to", "is required to", "will be required"]

# ─── Review flag patterns ──────────────────────────────────────────────────────
_FLAG_PATTERNS: list[tuple[str, str, str, str, str]] = [
    # (pattern, title, explanation, action, priority)
    (
        r"penalty|penalt|liquidated\s+damages",
        "Penalty / Liquidated Damages",
        "The document references penalties or liquidated damages. Review the triggering conditions and amounts.",
        "Clarify when penalties apply and whether the amounts are reasonable.",
        "HIGH",
    ),
    (
        r"auto.?renew|automatic\s+renewal",
        "Automatic Renewal Clause",
        "The document appears to contain automatic renewal terms. Failure to act by a specific date may extend obligations.",
        "Note any cancellation deadlines to avoid unwanted renewal.",
        "HIGH",
    ),
    (
        r"non.?compet|not\s+to\s+compete",
        "Non-Compete Restriction",
        "A non-compete clause restricts your ability to work in certain roles or industries after this agreement ends.",
        "Ask a lawyer to confirm the geographic scope, duration, and enforceability in your jurisdiction.",
        "HIGH",
    ),
    (
        r"limitation\s+of\s+liability|liability.{1,40}limited",
        "Limitation of Liability",
        "The document limits the liability of one or more parties. This may cap compensation in case of a dispute.",
        "Verify the liability cap amount and which parties are protected.",
        "MEDIUM",
    ),
    (
        r"indemnif",
        "Indemnification Obligation",
        "An indemnification clause requires one party to cover costs or losses incurred by the other party.",
        "Understand which events trigger indemnification and whether it is mutual.",
        "MEDIUM",
    ),
    (
        r"arbitrat",
        "Arbitration / Dispute Resolution",
        "The document requires disputes to be resolved through arbitration rather than court proceedings.",
        "Confirm the arbitration venue, governing rules, and whether class-action rights are waived.",
        "MEDIUM",
    ),
    (
        r"class\s+action\s+waiver|waive.*class",
        "Class Action Waiver",
        "The document may contain a class action waiver, preventing participation in group legal actions.",
        "Discuss implications with a lawyer — these waivers affect your legal remedies.",
        "HIGH",
    ),
    (
        r"unilateral.*amendment|amend.*sole\s+discretion",
        "Unilateral Amendment Rights",
        "One party may have the right to amend this agreement without your consent.",
        "Confirm whether you have a right to object or terminate upon changes.",
        "HIGH",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════


def generate_fallback_summary(doc: Document) -> DocumentSummary:
    """Generate a deterministic summary from document text."""
    text = doc.full_text.strip()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]

    # Quick summary: first meaningful paragraph
    quick = paragraphs[0] if paragraphs else (lines[0] if lines else "No content extracted.")
    if len(quick) > 350:
        quick = quick[:347] + "…"

    # Detect document type from metadata
    doc_type = doc.metadata.detected_type if doc.metadata else "Document"

    # Extract parties (simple heuristic)
    parties = _extract_parties(text)

    # Extract dates
    dates = _extract_dates(text)

    # Key points from sections
    key_points = _extract_key_points(text)

    # Effective date
    eff_date = _find_effective_date(text)

    detailed = (
        f"This is a {doc_type} containing approximately {doc.metadata.word_count:,} words "
        f"across {doc.metadata.page_count or len(doc.chunks)} "
        f"{'pages' if doc.metadata.page_count else 'sections'}. "
        "The analysis below is based on deterministic keyword extraction because AI enhancement "
        "is temporarily unavailable. Key topics detected include: "
        + ", ".join(_detect_topics(text))
        + ". Please review the full document carefully and consult a qualified attorney."
    )

    return DocumentSummary(
        quick_summary=quick,
        detailed_summary=detailed,
        executive_summary=(
            f"Document type: {doc_type}. "
            f"Parties identified: {', '.join(parties) if parties else 'See full document'}. "
            "AI analysis is temporarily unavailable — results are based on document text extraction. "
            "Consult a legal professional before taking action."
        ),
        key_points=key_points or ["Please review the full document text manually."],
        parties=parties,
        document_type=doc_type,
        effective_date=eff_date,
        key_dates=[f"Date reference: {d}" for d in dates[:6]],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CLAUSES
# ═══════════════════════════════════════════════════════════════════════════════


def extract_fallback_clauses(doc: Document) -> list[Clause]:
    """Extract clauses using keyword/regex heuristics across paragraphs."""
    text = doc.full_text
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 40]
    clauses: list[Clause] = []
    seen_categories: set[str] = set()

    for para in paragraphs:
        para_lower = para.lower()
        for category, terms in _CLAUSE_KEYWORDS.items():
            if category in seen_categories:
                continue
            if any(term in para_lower for term in terms):
                seen_categories.add(category)
                snippet = para[:600].strip()
                citation_text = para[:200].strip()

                # Determine priority
                high_categories = {
                    "Liability & Indemnity",
                    "Non-Compete / Non-Solicitation",
                    "Intellectual Property",
                }
                priority = "HIGH" if category in high_categories else "MEDIUM"

                clauses.append(
                    Clause(
                        category=category,
                        title=f"{category} Provision",
                        explanation=(
                            f"This section discusses {category.lower()} terms. "
                            "Review the specific language carefully. "
                            "(Extracted by keyword analysis — AI enhancement unavailable.)"
                        ),
                        original_text=snippet + ("…" if len(para) > 600 else ""),
                        citation=Citation(text=citation_text),
                        review_priority=priority,
                    )
                )

    if not clauses:
        clauses.append(
            Clause(
                category="General",
                title="Document Content",
                explanation=(
                    "No standard clause structures were automatically identified. "
                    "Please review the full document manually. "
                    "This may occur with non-standard formatting or very short documents."
                ),
                original_text="",
                citation=Citation(text=""),
                review_priority="LOW",
            )
        )

    return clauses


# ═══════════════════════════════════════════════════════════════════════════════
#  RISKS & OBLIGATIONS
# ═══════════════════════════════════════════════════════════════════════════════


def analyze_fallback_risks(doc: Document) -> tuple[list[ReviewFlag], list[Obligation]]:
    """Analyze review flags and obligations deterministically."""
    text = doc.full_text
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
    flags: list[ReviewFlag] = []
    obligations: list[Obligation] = []
    seen_flag_titles: set[str] = set()

    for para in paragraphs:
        para_lower = para.lower()
        snippet = para[:400].strip()

        # --- Flags ---
        for pattern, title, explanation, action, priority in _FLAG_PATTERNS:
            if title in seen_flag_titles:
                continue
            if re.search(pattern, para_lower):
                seen_flag_titles.add(title)
                flags.append(
                    ReviewFlag(
                        title=title,
                        explanation=explanation,
                        evidence=snippet + ("…" if len(para) > 400 else ""),
                        citation=Citation(text=para[:200].strip()),
                        review_priority=priority,
                        suggested_action=action,
                    )
                )

        # --- Obligations (limit to avoid noise) ---
        if len(obligations) < 8:
            for trigger in _OBLIGATION_TRIGGERS:
                if trigger in para_lower:
                    # Extract actor using simple patterns
                    actor = _extract_actor(para) or "A party"
                    obligations.append(
                        Obligation(
                            actor=actor,
                            obligation=snippet[:300] + ("…" if len(snippet) > 300 else ""),
                            deadline=_extract_deadline(para),
                            trigger=None,
                            citation=Citation(text=para[:200].strip()),
                            review_priority="MEDIUM",
                        )
                    )
                    break

    return flags, obligations


# ═══════════════════════════════════════════════════════════════════════════════
#  CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════


def generate_fallback_checklist(doc: Document) -> list[ChecklistItem]:
    """Generate a useful action checklist even without AI."""
    text = doc.full_text.lower()
    items: list[ChecklistItem] = [
        ChecklistItem(
            action="Read the entire document carefully before signing",
            responsible_party="You",
            deadline=None,
            priority="HIGH",
            source="General best practice",
            completed=False,
        ),
        ChecklistItem(
            action="Identify all parties, their roles, and contact information",
            responsible_party="You",
            deadline=None,
            priority="HIGH",
            source="Opening section",
            completed=False,
        ),
        ChecklistItem(
            action="Confirm the effective date and term/duration of the agreement",
            responsible_party="You",
            deadline=None,
            priority="HIGH",
            source="Term / Duration section",
            completed=False,
        ),
        ChecklistItem(
            action="List and calendar all key dates and deadlines mentioned",
            responsible_party="You",
            deadline=None,
            priority="HIGH",
            source="Throughout document",
            completed=False,
        ),
    ]

    # Conditional items based on document content
    if any(t in text for t in ["terminat", "cancel"]):
        items.append(
            ChecklistItem(
                action="Understand the termination procedure and required notice period",
                responsible_party="You",
                priority="HIGH",
                source="Termination clause",
                completed=False,
            )
        )

    if any(t in text for t in ["renew", "automatic renewal", "auto-renew"]):
        items.append(
            ChecklistItem(
                action="Check for automatic renewal clauses and note opt-out deadlines",
                responsible_party="You",
                priority="HIGH",
                source="Renewal clause",
                completed=False,
            )
        )

    if any(t in text for t in ["confidential", "non-disclosure"]):
        items.append(
            ChecklistItem(
                action="Understand the scope and duration of confidentiality obligations",
                responsible_party="You",
                priority="MEDIUM",
                source="Confidentiality clause",
                completed=False,
            )
        )

    if any(t in text for t in ["payment", "salary", "fee", "compensation"]):
        items.append(
            ChecklistItem(
                action="Verify payment terms, amounts, schedule, and conditions",
                responsible_party="You",
                priority="HIGH",
                source="Payment / Compensation section",
                completed=False,
            )
        )

    if any(t in text for t in ["non-compete", "not compete", "non-solicitation"]):
        items.append(
            ChecklistItem(
                action="Note any non-compete or non-solicitation restrictions and their duration",
                responsible_party="You",
                priority="HIGH",
                source="Non-compete / Non-solicitation clause",
                completed=False,
            )
        )

    if any(t in text for t in ["intellectual property", "work product", "ip rights"]):
        items.append(
            ChecklistItem(
                action="Review who owns intellectual property created during this agreement",
                responsible_party="You",
                priority="HIGH",
                source="Intellectual Property clause",
                completed=False,
            )
        )

    items.append(
        ChecklistItem(
            action="Consult a qualified attorney before signing",
            responsible_party="You",
            deadline=None,
            priority="HIGH",
            source="LegalLens AI recommendation",
            completed=False,
        )
    )

    return items


# ═══════════════════════════════════════════════════════════════════════════════
#  LAWYER QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def generate_fallback_lawyer_questions(doc: Document) -> list[LawyerQuestion]:
    """Generate practical questions for a legal professional, based on document content."""
    text = doc.full_text.lower()
    questions: list[LawyerQuestion] = [
        LawyerQuestion(
            question="What are my exact legal obligations under this agreement, and what happens if I fail to meet them?",
            context="Understanding obligations is fundamental before signing any legal document.",
            related_clause="General obligations",
            priority="HIGH",
        ),
        LawyerQuestion(
            question="Are there any clauses in this document that are unusual, overly broad, or potentially unfair?",
            context="A lawyer can identify non-standard terms that may pose risks.",
            related_clause="General",
            priority="HIGH",
        ),
    ]

    if any(t in text for t in ["terminat", "cancel"]):
        questions.append(
            LawyerQuestion(
                question="Under what conditions can either party terminate this agreement, and what are the consequences?",
                context="Understanding exit rights is critical to managing risk.",
                related_clause="Termination",
                priority="HIGH",
            )
        )

    if any(t in text for t in ["renew", "automatic renewal"]):
        questions.append(
            LawyerQuestion(
                question="Is renewal automatic? What steps must I take to opt out, and by when?",
                context="Missing an opt-out deadline may result in unwanted obligations.",
                related_clause="Renewal",
                priority="HIGH",
            )
        )

    if any(t in text for t in ["confidential", "non-disclosure"]):
        questions.append(
            LawyerQuestion(
                question="How long do confidentiality obligations continue after the agreement ends?",
                context="Post-termination obligations can significantly impact future activities.",
                related_clause="Confidentiality",
                priority="MEDIUM",
            )
        )

    if any(t in text for t in ["indemnif", "hold harmless"]):
        questions.append(
            LawyerQuestion(
                question="Who bears indemnification obligations and are they mutual or one-sided?",
                context="Indemnification clauses can create significant financial exposure.",
                related_clause="Indemnity",
                priority="HIGH",
            )
        )

    if any(t in text for t in ["non-compete", "not compete"]):
        questions.append(
            LawyerQuestion(
                question="Is the non-compete clause enforceable in my jurisdiction? What are its geographic and time limits?",
                context="Non-compete enforceability varies significantly by state and country.",
                related_clause="Non-Compete",
                priority="HIGH",
            )
        )

    if any(t in text for t in ["arbitrat", "dispute resolution"]):
        questions.append(
            LawyerQuestion(
                question="What are the implications of the arbitration clause, and do I waive my right to a jury trial?",
                context="Arbitration clauses alter how disputes are resolved and can limit legal options.",
                related_clause="Dispute Resolution",
                priority="MEDIUM",
            )
        )

    if any(t in text for t in ["intellectual property", "work product", "assigns"]):
        questions.append(
            LawyerQuestion(
                question="Who owns intellectual property I create, and does this include work done on my own time?",
                context="IP assignment clauses can be very broad and may affect personal projects.",
                related_clause="Intellectual Property",
                priority="HIGH",
            )
        )

    questions.append(
        LawyerQuestion(
            question="Are there any provisions in this document that I should negotiate or request modification of?",
            context="A lawyer can advise on negotiable terms to better protect your interests.",
            related_clause="General",
            priority="MEDIUM",
        )
    )

    return questions


# ═══════════════════════════════════════════════════════════════════════════════
#  Q&A
# ═══════════════════════════════════════════════════════════════════════════════


def fallback_qa(doc: Document, question: str) -> QAResponse:
    """Deterministic Q&A using TF-IDF retrieval on document chunks."""
    disclaimer = get_advice_disclaimer(question)

    relevant_chunks = retrieve_relevant_chunks(
        query=question,
        chunks=doc.chunks,
        top_k=3,
    )

    if not relevant_chunks:
        return QAResponse(
            question=question,
            answer=(
                "I searched the document but could not find information specifically relevant to your question. "
                "Note: AI analysis is temporarily unavailable, so this used keyword-based search. "
                "If you believe the document contains this information, please review it manually."
            ),
            citations=[],
            grounding_status="not_found",
            confidence="low",
            disclaimer=disclaimer or "",
        )

    # Construct extractive answer
    answer_parts = [
        "AI analysis is temporarily unavailable. "
        "The following excerpts from your document are most relevant to your question:\n"
    ]
    citations: list[Citation] = []

    for i, chunk in enumerate(relevant_chunks, 1):
        excerpt = chunk.text.strip()
        if len(excerpt) > 400:
            excerpt = excerpt[:397] + "…"
        answer_parts.append(f'{i}. "{excerpt}"')
        citations.append(
            Citation(
                text=excerpt,
                page=chunk.page,
                section=chunk.section or f"Section {chunk.chunk_id + 1}",
            )
        )

    answer_parts.append(
        "\nPlease review these excerpts in context. "
        "For a definitive interpretation, consult a qualified attorney."
    )

    return QAResponse(
        question=question,
        answer="\n\n".join(answer_parts),
        citations=citations,
        grounding_status="partially_grounded",
        confidence="low",
        disclaimer=disclaimer or "",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════


def fallback_compare(doc_a: Document, doc_b: Document) -> ComparisonResult:
    """Deterministic comparison using difflib and keyword analysis."""
    # Topic-level comparison
    items: list[ComparisonItem] = []

    for category, terms in _CLAUSE_KEYWORDS.items():
        a_has = any(t in doc_a.full_text.lower() for t in terms)
        b_has = any(t in doc_b.full_text.lower() for t in terms)

        if not a_has and not b_has:
            continue

        status: str
        if a_has and b_has:
            status = "unchanged"
            expl = f"Both documents appear to address {category.lower()}."
        elif a_has and not b_has:
            status = "removed"
            expl = f"Document A addresses {category.lower()}, but Document B does not appear to."
        else:
            status = "added"
            expl = f"Document B addresses {category.lower()}, but Document A does not appear to."

        items.append(
            ComparisonItem(
                category=category,
                document_a="Present" if a_has else "Not identified",
                document_b="Present" if b_has else "Not identified",
                status=status,
                explanation=expl,
            )
        )

    # Raw line diff summary
    lines_a = doc_a.full_text.splitlines()
    lines_b = doc_b.full_text.splitlines()
    diff = list(difflib.unified_diff(lines_a, lines_b, lineterm=""))
    added_lines = sum(1 for ln in diff if ln.startswith("+") and not ln.startswith("+++"))
    removed_lines = sum(1 for ln in diff if ln.startswith("-") and not ln.startswith("---"))

    summary = (
        f"Deterministic topic comparison completed (AI enhancement unavailable). "
        f"At topic level: {sum(1 for i in items if i.status == 'changed')} changed, "
        f"{sum(1 for i in items if i.status == 'added')} topics only in B, "
        f"{sum(1 for i in items if i.status == 'removed')} topics only in A. "
        f"Raw text: approximately {added_lines} lines added, {removed_lines} lines removed."
    )

    key_diffs = [f"{i.category}: {i.status.upper()}" for i in items if i.status != "unchanged"] or [
        "No significant topic-level differences detected."
    ]

    return ComparisonResult(
        document_a_name=doc_a.filename,
        document_b_name=doc_b.filename,
        items=items,
        summary=summary,
        key_differences=key_diffs[:10],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_parties(text: str) -> list[str]:
    """Extract party names using common legal patterns."""
    parties: list[str] = []

    # "between X and Y"
    m = re.search(
        r"between\s+([A-Z][A-Za-z\s,\.]+?)\s+(?:and|&)\s+([A-Z][A-Za-z\s,\.]+?)[\.,\n]", text
    )
    if m:
        parties.extend([m.group(1).strip(), m.group(2).strip()])
        return parties[:4]

    # "Party A:" or "EMPLOYER:" / "EMPLOYEE:"
    for pattern in [
        r"(EMPLOYER|EMPLOYEE|CLIENT|VENDOR|COMPANY|LICENSOR|LICENSEE|BUYER|SELLER|LESSOR|LESSEE)\s*[:\-]\s*([A-Z][A-Za-z\s,\.]+?)[\.,\n]",
        r'"([A-Z][a-z]+)"\s+means\s+([A-Z][A-Za-z\s,\.]+?)[\.,]',
    ]:
        for m in re.finditer(pattern, text):
            role = m.group(1).strip()
            name = m.group(2).strip()
            parties.append(f"{name} ({role})")
            if len(parties) >= 4:
                return parties

    return parties


def _extract_dates(text: str) -> list[str]:
    """Extract date references from text."""
    patterns = [
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    ]
    dates: list[str] = []
    for p in patterns:
        dates.extend(re.findall(p, text))
    return list(dict.fromkeys(dates))  # deduplicate preserving order


def _find_effective_date(text: str) -> str | None:
    """Try to find the effective/commencement date."""
    patterns = [
        r"effective\s+(?:as\s+of\s+|date\s+of\s+)?(?:the\s+)?(\d{1,2}\s+\w+\s+\d{4})",
        r"effective\s+(?:as\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        r"entered\s+into\s+(?:as\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        r"made\s+(?:on\s+|this\s+)(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def _extract_key_points(text: str) -> list[str]:
    """Detect broad topic areas covered by the document."""
    points: list[str] = []
    text_lower = text.lower()

    checks = [
        (["employ", "employer", "employee"], "Employment relationship established"),
        (["salary", "compensation", "base salary"], "Compensation terms specified"),
        (["confidential", "non-disclosure"], "Confidentiality obligations included"),
        (["terminat", "cancel"], "Termination conditions defined"),
        (["intellectual property", "work product"], "Intellectual property rights addressed"),
        (["non-compete", "not compete"], "Non-compete restrictions included"),
        (["renew", "automatic renewal"], "Renewal terms present"),
        (["arbitrat", "dispute"], "Dispute resolution mechanism specified"),
        (["governing law", "jurisdiction"], "Governing law specified"),
        (["indemnif", "hold harmless"], "Indemnification provisions included"),
    ]

    for triggers, label in checks:
        if any(t in text_lower for t in triggers):
            points.append(label)

    return points[:8]


def _detect_topics(text: str) -> list[str]:
    """Return a short list of detected topics for the detailed summary."""
    topics: list[str] = []
    for category, terms in _CLAUSE_KEYWORDS.items():
        if any(t in text.lower() for t in terms):
            topics.append(category)
    return topics[:6] or ["General terms"]


def _extract_actor(para: str) -> str | None:
    """Try to extract the obligated party from a paragraph."""
    # Look for capitalized entity at start
    m = re.match(r"^([A-Z][a-zA-Z\s]{2,30})\s+(?:shall|must|agrees)", para.strip())
    if m:
        return m.group(1).strip()
    # Common roles
    for role in [
        "Employee",
        "Employer",
        "Company",
        "Contractor",
        "Client",
        "Vendor",
        "Licensor",
        "Licensee",
        "Buyer",
        "Seller",
    ]:
        if re.search(r"\b" + role + r"\b", para):
            return role
    return None


def _extract_deadline(para: str) -> str | None:
    """Try to extract a deadline from a paragraph."""
    m = re.search(
        r"within\s+(\d+\s+(?:day|business day|week|month|calendar day)s?)",
        para,
        re.IGNORECASE,
    )
    if m:
        return m.group(0).strip()
    dates = _extract_dates(para)
    return dates[0] if dates else None

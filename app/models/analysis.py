"""LegalLens AI — Analysis models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Source reference for a finding."""

    page: int | None = Field(default=None, description="Page number (1-indexed)")
    section: str | None = Field(default=None, description="Section heading")
    text: str = Field(default="", description="Supporting evidence text")


class Clause(BaseModel):
    """Extracted document clause."""

    category: str = Field(description="Clause category")
    title: str = Field(default="", description="Short clause title")
    explanation: str = Field(description="Plain-language explanation")
    original_text: str = Field(default="", description="Original clause text from document")
    citation: Citation = Field(default_factory=Citation)
    review_priority: str = Field(default="LOW", description="LOW, MEDIUM, HIGH, REVIEW")


class ReviewFlag(BaseModel):
    """Document review flag — a potential concern, NOT a legal verdict."""

    title: str = Field(description="Short flag title")
    explanation: str = Field(description="Why this deserves attention")
    evidence: str = Field(default="", description="Supporting text from document")
    citation: Citation = Field(default_factory=Citation)
    review_priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, REVIEW")
    suggested_action: str = Field(default="", description="Suggested next step")


class Obligation(BaseModel):
    """Explicit obligation extracted from document."""

    actor: str = Field(description="Who has the obligation")
    obligation: str = Field(description="What must be done")
    deadline: str | None = Field(default=None, description="Deadline if stated")
    trigger: str | None = Field(default=None, description="Triggering event")
    citation: Citation = Field(default_factory=Citation)
    review_priority: str = Field(default="MEDIUM")


class DocumentSummary(BaseModel):
    """Multi-level document summary."""

    quick_summary: str = Field(default="", description="2-3 sentence summary")
    detailed_summary: str = Field(default="", description="Detailed summary")
    executive_summary: str = Field(default="", description="Executive-level summary")
    key_points: list[str] = Field(default_factory=list)
    parties: list[str] = Field(default_factory=list)
    document_type: str = Field(default="Unknown")
    effective_date: str | None = Field(default=None)
    key_dates: list[str] = Field(default_factory=list)


class QAResponse(BaseModel):
    """Question-answer response with grounding."""

    question: str = Field(description="Original question")
    answer: str = Field(description="AI-generated answer")
    citations: list[Citation] = Field(default_factory=list)
    grounding_status: str = Field(
        default="grounded",
        description="grounded, partially_grounded, not_found, general_info",
    )
    confidence: str = Field(default="medium", description="low, medium, high")
    disclaimer: str = Field(default="")


class ComparisonItem(BaseModel):
    """Single comparison point between two documents."""

    category: str = Field(description="What is being compared")
    document_a: str = Field(default="", description="Document A content")
    document_b: str = Field(default="", description="Document B content")
    status: str = Field(default="unchanged", description="added, removed, changed, unchanged")
    explanation: str = Field(default="", description="Difference explanation")


class ComparisonResult(BaseModel):
    """Full document comparison result."""

    document_a_name: str = Field(description="Document A filename")
    document_b_name: str = Field(description="Document B filename")
    items: list[ComparisonItem] = Field(default_factory=list)
    summary: str = Field(default="", description="Overall comparison summary")
    key_differences: list[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    """Actionable checklist item."""

    action: str = Field(description="Action to take")
    responsible_party: str = Field(default="", description="Who should act")
    deadline: str | None = Field(default=None, description="Deadline if stated")
    priority: str = Field(default="MEDIUM")
    source: str = Field(default="", description="Where in document")
    completed: bool = Field(default=False)


class LawyerQuestion(BaseModel):
    """Question prepared for a legal professional."""

    question: str = Field(description="Question text")
    context: str = Field(default="", description="Why this question matters")
    related_clause: str = Field(default="", description="Related clause/section")
    priority: str = Field(default="MEDIUM")


class DocumentAnalysis(BaseModel):
    """Complete document analysis result — the Legal Action Map."""

    document_id: str = Field(description="Source document ID")
    summary: DocumentSummary = Field(default_factory=DocumentSummary)
    clauses: list[Clause] = Field(default_factory=list)
    review_flags: list[ReviewFlag] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    lawyer_questions: list[LawyerQuestion] = Field(default_factory=list)
    disclaimer: str = Field(default="")

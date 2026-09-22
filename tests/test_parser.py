"""LegalLens AI — Tests for AI response parsers."""

from __future__ import annotations

import json

import pytest

from app.ai.client import AIClientError
from app.ai.parser import (
    _get_list,
    _get_priority,
    _get_str,
    parse_checklist_response,
    parse_clauses_response,
    parse_comparison_response,
    parse_lawyer_questions_response,
    parse_qa_response,
    parse_risk_response,
    parse_summary_response,
)


def _json(data: dict) -> str:
    return json.dumps(data)


class TestParseSummaryResponse:
    def test_full_response(self):
        raw = _json(
            {
                "quick_summary": "Quick",
                "detailed_summary": "Detailed",
                "executive_summary": "Executive",
                "key_points": ["Point 1", "Point 2"],
                "parties": ["Party A", "Party B"],
                "document_type": "NDA",
                "effective_date": "2025-01-01",
                "key_dates": ["Jan 1", "Dec 31"],
            }
        )
        result = parse_summary_response(raw)
        assert result.quick_summary == "Quick"
        assert result.detailed_summary == "Detailed"
        assert result.executive_summary == "Executive"
        assert result.key_points == ["Point 1", "Point 2"]
        assert result.parties == ["Party A", "Party B"]
        assert result.document_type == "NDA"
        assert result.effective_date == "2025-01-01"

    def test_partial_response_uses_defaults(self):
        raw = _json({"quick_summary": "Summary only"})
        result = parse_summary_response(raw)
        assert result.quick_summary == "Summary only"
        assert result.detailed_summary == ""
        assert result.key_points == []
        assert result.parties == []

    def test_null_values_use_defaults(self):
        raw = _json({"quick_summary": None, "key_points": None})
        result = parse_summary_response(raw)
        assert result.quick_summary == ""
        assert result.key_points == []

    def test_invalid_json_raises(self):
        with pytest.raises(AIClientError):
            parse_summary_response("not json at all")


class TestParseClausesResponse:
    def test_full_clause_list(self):
        raw = _json(
            {
                "clauses": [
                    {
                        "category": "Payment",
                        "title": "Monthly Fees",
                        "explanation": "Pay monthly",
                        "original_text": "Payment due on 1st",
                        "review_priority": "HIGH",
                        "page": 2,
                        "section": "Section 3",
                        "text": "Payment due on 1st",
                    }
                ]
            }
        )
        result = parse_clauses_response(raw)
        assert len(result) == 1
        assert result[0].category == "Payment"
        assert result[0].title == "Monthly Fees"
        assert result[0].review_priority == "HIGH"
        assert result[0].citation.page == 2

    def test_empty_clauses_list(self):
        raw = _json({"clauses": []})
        assert parse_clauses_response(raw) == []

    def test_missing_clauses_key(self):
        raw = _json({})
        assert parse_clauses_response(raw) == []

    def test_non_list_clauses_returns_empty(self):
        raw = _json({"clauses": "not a list"})
        assert parse_clauses_response(raw) == []

    def test_malformed_item_skipped(self):
        raw = _json(
            {
                "clauses": [
                    "not a dict",
                    {"category": "Payment", "explanation": "Pay"},
                ]
            }
        )
        result = parse_clauses_response(raw)
        assert len(result) == 1
        assert result[0].category == "Payment"

    def test_invalid_priority_defaults_to_medium(self):
        raw = _json(
            {"clauses": [{"category": "Misc", "explanation": "X", "review_priority": "INVALID"}]}
        )
        result = parse_clauses_response(raw)
        assert result[0].review_priority == "MEDIUM"


class TestParseRiskResponse:
    def test_full_risk_response(self):
        raw = _json(
            {
                "review_flags": [
                    {
                        "title": "Auto-renewal",
                        "explanation": "Contract auto-renews",
                        "review_priority": "HIGH",
                        "suggested_action": "Verify renewal dates",
                        "text": "auto-renews annually",
                    }
                ],
                "obligations": [
                    {
                        "actor": "Party A",
                        "obligation": "Pay monthly fees",
                        "deadline": "1st of each month",
                        "trigger": "Service activation",
                        "review_priority": "MEDIUM",
                    }
                ],
            }
        )
        flags, obligations = parse_risk_response(raw)
        assert len(flags) == 1
        assert flags[0].title == "Auto-renewal"
        assert flags[0].review_priority == "HIGH"
        assert flags[0].suggested_action == "Verify renewal dates"
        assert len(obligations) == 1
        assert obligations[0].actor == "Party A"
        assert obligations[0].deadline == "1st of each month"

    def test_empty_response(self):
        raw = _json({"review_flags": [], "obligations": []})
        flags, obligations = parse_risk_response(raw)
        assert flags == []
        assert obligations == []

    def test_missing_keys_returns_empty_lists(self):
        raw = _json({})
        flags, obligations = parse_risk_response(raw)
        assert flags == []
        assert obligations == []

    def test_malformed_items_skipped(self):
        raw = _json({"review_flags": ["not a dict"], "obligations": [42]})
        flags, obligations = parse_risk_response(raw)
        assert flags == []
        assert obligations == []


class TestParseQAResponse:
    def test_grounded_response(self):
        raw = _json(
            {
                "answer": "The notice period is 30 days.",
                "grounding_status": "grounded",
                "confidence": "high",
                "citations": [{"text": "30 days written notice", "page": 3}],
            }
        )
        result = parse_qa_response(raw, "What is the notice period?")
        assert result.question == "What is the notice period?"
        assert result.answer == "The notice period is 30 days."
        assert result.grounding_status == "grounded"
        assert result.confidence == "high"
        assert len(result.citations) == 1
        assert result.citations[0].page == 3

    def test_missing_answer_uses_default(self):
        raw = _json({})
        result = parse_qa_response(raw, "Question?")
        assert result.answer == "I was unable to process this question."

    def test_empty_citations_list(self):
        raw = _json({"answer": "Found it", "citations": []})
        result = parse_qa_response(raw, "Q?")
        assert result.citations == []

    def test_non_dict_citations_skipped(self):
        raw = _json({"answer": "Found it", "citations": ["not a dict", {"text": "evidence"}]})
        result = parse_qa_response(raw, "Q?")
        assert len(result.citations) == 1


class TestParseComparisonResponse:
    def test_full_comparison(self):
        raw = _json(
            {
                "summary": "Contracts differ in payment terms",
                "key_differences": ["Payment changed", "Notice period added"],
                "items": [
                    {
                        "category": "Payment",
                        "document_a": "Monthly",
                        "document_b": "Quarterly",
                        "status": "changed",
                        "explanation": "Payment frequency changed",
                    }
                ],
            }
        )
        result = parse_comparison_response(raw, "doc_a.pdf", "doc_b.pdf")
        assert result.document_a_name == "doc_a.pdf"
        assert result.document_b_name == "doc_b.pdf"
        assert result.summary == "Contracts differ in payment terms"
        assert len(result.items) == 1
        assert result.items[0].status == "changed"

    def test_empty_items(self):
        raw = _json({"summary": "No changes", "items": []})
        result = parse_comparison_response(raw, "a.pdf", "b.pdf")
        assert result.items == []

    def test_malformed_item_skipped(self):
        raw = _json({"items": ["string_not_dict", {"category": "Payment", "status": "added"}]})
        result = parse_comparison_response(raw, "a.pdf", "b.pdf")
        assert len(result.items) == 1


class TestParseChecklistResponse:
    def test_full_checklist(self):
        raw = _json(
            {
                "checklist": [
                    {
                        "action": "Sign agreement",
                        "responsible_party": "Party A",
                        "deadline": "Jan 15",
                        "review_priority": "HIGH",
                        "source": "Section 1",
                    }
                ]
            }
        )
        result = parse_checklist_response(raw)
        assert len(result) == 1
        assert result[0].action == "Sign agreement"
        assert result[0].responsible_party == "Party A"
        assert result[0].deadline == "Jan 15"

    def test_empty_checklist(self):
        raw = _json({"checklist": []})
        assert parse_checklist_response(raw) == []


class TestParseLawyerQuestionsResponse:
    def test_full_questions(self):
        raw = _json(
            {
                "questions": [
                    {
                        "question": "What does the liability cap mean?",
                        "context": "Clause limits liability",
                        "related_clause": "Section 5",
                        "review_priority": "HIGH",
                    }
                ]
            }
        )
        result = parse_lawyer_questions_response(raw)
        assert len(result) == 1
        assert result[0].question == "What does the liability cap mean?"
        assert result[0].priority == "HIGH"

    def test_empty_questions(self):
        raw = _json({"questions": []})
        assert parse_lawyer_questions_response(raw) == []


class TestHelperFunctions:
    def test_get_str_existing_key(self):
        assert _get_str({"key": "value"}, "key") == "value"

    def test_get_str_missing_key(self):
        assert _get_str({}, "key") == ""

    def test_get_str_with_default(self):
        assert _get_str({}, "key", "default") == "default"

    def test_get_str_none_value(self):
        assert _get_str({"key": None}, "key") == ""

    def test_get_list_valid(self):
        assert _get_list({"items": ["a", "b"]}, "items") == ["a", "b"]

    def test_get_list_missing_key(self):
        assert _get_list({}, "items") == []

    def test_get_list_not_a_list(self):
        assert _get_list({"items": "string"}, "items") == []

    def test_get_list_filters_none(self):
        result = _get_list({"items": ["a", None, "b"]}, "items")
        assert result == ["a", "b"]

    def test_get_priority_valid(self):
        assert _get_priority({"review_priority": "HIGH"}) == "HIGH"
        assert _get_priority({"review_priority": "low"}) == "LOW"

    def test_get_priority_invalid_defaults_medium(self):
        assert _get_priority({"review_priority": "CRITICAL"}) == "MEDIUM"

    def test_get_priority_missing_defaults_medium(self):
        assert _get_priority({}) == "MEDIUM"

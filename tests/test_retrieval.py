"""LegalLens AI — Tests for retrieval and context assembly."""

from __future__ import annotations

from app.ai.retrieval import _tokenize, assemble_context, retrieve_relevant_chunks
from app.models.document import DocumentChunk


def _make_chunk(
    chunk_id: int, text: str, page: int = 1, section: str | None = None
) -> DocumentChunk:
    """Factory for DocumentChunk in tests."""
    return DocumentChunk(
        chunk_id=chunk_id,
        text=text,
        page=page,
        section=section,
        start_char=0,
        end_char=len(text),
    )


class TestRetrieveRelevantChunks:
    """Tests for TF-IDF retrieval."""

    def test_empty_query_returns_empty(self):
        chunks = [_make_chunk(0, "some legal text")]
        assert retrieve_relevant_chunks("", chunks) == []

    def test_empty_chunks_returns_empty(self):
        assert retrieve_relevant_chunks("termination", []) == []

    def test_fewer_chunks_than_top_k_returns_all(self):
        chunks = [_make_chunk(0, "termination clause"), _make_chunk(1, "payment terms")]
        result = retrieve_relevant_chunks("termination", chunks, top_k=10)
        assert len(result) == 2

    def test_top_k_limits_results(self):
        chunks = [_make_chunk(i, f"some text about topic {i}") for i in range(20)]
        result = retrieve_relevant_chunks("topic", chunks, top_k=5)
        assert len(result) == 5

    def test_relevant_chunk_ranked_first(self):
        """The chunk most closely matching the query should rank higher."""
        # Need more than top_k chunks so scoring actually runs
        chunks = [
            _make_chunk(0, "The weather is sunny today and tomorrow"),
            _make_chunk(1, "Termination requires thirty days written notice from either party"),
            _make_chunk(2, "Payment shall be made monthly in advance"),
            _make_chunk(3, "Confidentiality obligations apply for two years"),
            _make_chunk(4, "Governing law is state of California"),
            _make_chunk(5, "Indemnification covers third party claims"),
            _make_chunk(6, "Liability limited to amounts paid in prior month"),
            _make_chunk(7, "Renewal occurs annually unless cancelled"),
            _make_chunk(8, "Intellectual property stays with the disclosing party"),
            _make_chunk(9, "Dispute resolution uses binding arbitration"),
            _make_chunk(10, "Force majeure covers natural disasters"),
        ]
        result = retrieve_relevant_chunks("termination notice period", chunks, top_k=5)
        # The termination chunk should be in the results
        chunk_ids = [c.chunk_id for c in result]
        assert 1 in chunk_ids

    def test_irrelevant_query_still_returns_chunks(self):
        """Even with no matching terms, chunks are returned (fallback to all)."""
        chunks = [_make_chunk(0, "legal agreement"), _make_chunk(1, "payment terms")]
        # "xyzzy" won't match anything — tokenizer should return terms or empty
        result = retrieve_relevant_chunks("xyzzy", chunks, top_k=5)
        # All chunks returned since len <= top_k
        assert len(result) == 2

    def test_deterministic_ordering(self):
        """Same inputs must produce same outputs."""
        chunks = [_make_chunk(i, f"clause {i} about termination payment notice") for i in range(10)]
        r1 = retrieve_relevant_chunks("termination payment", chunks, top_k=5)
        r2 = retrieve_relevant_chunks("termination payment", chunks, top_k=5)
        assert [c.chunk_id for c in r1] == [c.chunk_id for c in r2]

    def test_stopwords_ignored(self):
        """Stopwords should not inflate scores."""
        # Need more chunks than top_k for scoring to activate
        chunks = [
            _make_chunk(0, "the and or but is are"),  # only stopwords
            _make_chunk(1, "termination notice clause"),
            _make_chunk(2, "payment monthly advance"),
            _make_chunk(3, "confidentiality obligations"),
            _make_chunk(4, "governing law california"),
            _make_chunk(5, "indemnification third party"),
            _make_chunk(6, "liability limited amounts"),
            _make_chunk(7, "renewal annually cancelled"),
            _make_chunk(8, "intellectual property disclosing"),
            _make_chunk(9, "dispute resolution arbitration"),
            _make_chunk(10, "force majeure disasters"),
        ]
        result = retrieve_relevant_chunks("the termination notice", chunks, top_k=3)
        # Termination chunk should be in top-k results
        chunk_ids = [c.chunk_id for c in result]
        assert 1 in chunk_ids


class TestAssembleContext:
    """Tests for context assembly."""

    def test_basic_assembly(self):
        chunks = [_make_chunk(0, "First clause text", page=1, section="Introduction")]
        result = assemble_context(chunks)
        assert "First clause text" in result
        assert "Page 1" in result
        assert "Introduction" in result

    def test_no_page_or_section(self):
        chunks = [_make_chunk(0, "Some text")]
        result = assemble_context(chunks)
        assert "Some text" in result

    def test_max_chars_respected(self):
        long_text = "a" * 10000
        chunks = [_make_chunk(0, long_text)]
        result = assemble_context(chunks, max_chars=500)
        assert len(result) <= 600  # slight buffer for separator

    def test_multiple_chunks_separated(self):
        chunks = [
            _make_chunk(0, "First part", page=1),
            _make_chunk(1, "Second part", page=2),
        ]
        result = assemble_context(chunks)
        assert "First part" in result
        assert "Second part" in result

    def test_empty_chunks_returns_empty_string(self):
        assert assemble_context([]) == ""

    def test_context_truncated_at_limit(self):
        """Context should stop adding chunks once max_chars is reached."""
        chunks = [_make_chunk(i, f"Chunk {i}: " + "x" * 2000) for i in range(10)]
        result = assemble_context(chunks, max_chars=3000)
        # Should not contain all 10 chunks worth of data
        assert len(result) <= 3100


class TestTokenize:
    """Tests for the internal tokenizer."""

    def test_basic_tokenization(self):
        tokens = _tokenize("Termination of Employment Agreement")
        assert "termination" in tokens
        assert "employment" in tokens
        assert "agreement" in tokens

    def test_stopwords_removed(self):
        tokens = _tokenize("the and or but is are of")
        assert tokens == []

    def test_short_tokens_removed(self):
        tokens = _tokenize("a b c abc")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "abc" in tokens

    def test_numbers_included(self):
        tokens = _tokenize("30 days notice")
        assert "30" in tokens

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_punctuation_stripped(self):
        tokens = _tokenize("termination, notice; period.")
        assert "termination" in tokens
        assert "notice" in tokens
        assert "period" in tokens

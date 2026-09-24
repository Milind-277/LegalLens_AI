"""LegalLens AI — Tests for AI client abstraction."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ai.client import AIClient, AIClientError, _find_json_in_text, parse_json_response


class TestParseJsonResponse:
    """Tests for JSON parsing from raw LLM output."""

    def test_clean_json(self):
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_fence_json(self):
        raw = '```json\n{"key": "value"}\n```'
        assert parse_json_response(raw) == {"key": "value"}

    def test_markdown_fence_no_language(self):
        raw = '```\n{"key": "value"}\n```'
        assert parse_json_response(raw) == {"key": "value"}

    def test_json_embedded_in_text(self):
        raw = 'Here is the analysis: {"key": "value"} Hope that helps!'
        assert parse_json_response(raw) == {"key": "value"}

    def test_nested_json(self):
        raw = '{"outer": {"inner": "value"}}'
        result = parse_json_response(raw)
        assert result["outer"]["inner"] == "value"

    def test_json_array_raises(self):
        """Non-dict JSON (array) should raise."""
        with pytest.raises(AIClientError, match="not a JSON object"):
            parse_json_response("[1, 2, 3]")

    def test_completely_invalid_raises(self):
        with pytest.raises(AIClientError):
            parse_json_response("this is not JSON")

    def test_empty_string_raises(self):
        with pytest.raises(AIClientError):
            parse_json_response("")

    def test_whitespace_only_raises(self):
        with pytest.raises(AIClientError):
            parse_json_response("   ")


class TestFindJsonInText:
    """Tests for the JSON extraction fallback."""

    def test_finds_embedded_json(self):
        result = _find_json_in_text('some text {"key": "val"} more text')
        assert result == {"key": "val"}

    def test_no_json_returns_none(self):
        assert _find_json_in_text("no json here") is None

    def test_malformed_json_returns_none(self):
        assert _find_json_in_text("{not valid json}") is None

    def test_empty_string_returns_none(self):
        assert _find_json_in_text("") is None


class TestAIClient:
    """Tests for AIClient initialization and error handling."""

    def test_missing_api_key_raises(self):
        client = AIClient(api_key="")
        with pytest.raises(AIClientError, match="API key"):
            client._ensure_initialized()

    def test_placeholder_api_key_raises(self):
        client = AIClient(api_key="your_api_key_here")
        with pytest.raises(AIClientError, match="API key"):
            client._ensure_initialized()

    def test_generate_raises_without_initialization(self):
        client = AIClient(api_key="")
        with pytest.raises(AIClientError):
            client.generate("test prompt")

    def test_generate_calls_model(self):
        """Test that generate calls through to the model correctly."""
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"result": "answer"}'
        mock_model.generate_content.return_value = mock_response
        client._model = mock_model

        result = client.generate("What is the notice period?")
        assert result == '{"result": "answer"}'
        mock_model.generate_content.assert_called_once()

    def test_generate_raises_on_empty_response(self):
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_model.generate_content.return_value = mock_response
        client._model = mock_model

        with pytest.raises(AIClientError, match="Empty response"):
            client.generate("test")

    def test_generate_raises_on_none_response(self):
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_model.generate_content.return_value = None
        client._model = mock_model

        with pytest.raises(AIClientError):
            client.generate("test")

    def test_generate_wraps_sdk_exception(self):
        """SDK exceptions should be wrapped in AIClientError."""
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Connection refused")
        client._model = mock_model

        with pytest.raises(AIClientError):
            client.generate("test")

    def test_rate_limit_error_is_not_retriable(self):
        """429 quota exhaustion should fail fast and trigger fallback, not retry storm."""
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("429 Too Many Requests")
        client._model = mock_model

        with pytest.raises(AIClientError) as exc_info:
            client.generate("test")
        assert exc_info.value.retriable is False

    def test_quota_error_message_mentions_quota(self):
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
        client._model = mock_model

        with pytest.raises(AIClientError, match="quota") as exc_info:
            client.generate("test")
        assert "quota" in str(exc_info.value).lower()

    def test_503_error_is_retriable(self):
        """503 errors should be marked retriable."""
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("503 Service Unavailable")
        client._model = mock_model

        with pytest.raises(AIClientError) as exc_info:
            client.generate("test")
        assert exc_info.value.retriable is True

    def test_generate_json_returns_dict(self):
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"answer": "yes"}'
        mock_model.generate_content.return_value = mock_response
        client._model = mock_model

        result = client.generate_json("Give me JSON")
        assert result == {"answer": "yes"}

    def test_system_instruction_included_in_prompt(self):
        """System instruction should be prepended to the prompt."""
        client = AIClient(api_key="test-key")
        client._initialized = True

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"ok": true}'
        mock_model.generate_content.return_value = mock_response
        client._model = mock_model

        client.generate("user prompt", system_instruction="system instructions")
        call_args = mock_model.generate_content.call_args
        # The prompt passed should contain both system and user content
        actual_prompt = call_args[0][0]
        assert "system instructions" in actual_prompt
        assert "user prompt" in actual_prompt

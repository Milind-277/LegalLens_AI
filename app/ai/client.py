"""LegalLens AI — AI client abstraction with retry and structured output."""

from __future__ import annotations

import json
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# Default model supported by the current Gemini API
DEFAULT_MODEL = "gemini-3.6-flash"


class AIClientError(Exception):
    """Raised when the AI client encounters an error."""

    def __init__(self, message: str, retriable: bool = False) -> None:
        self.retriable = retriable
        super().__init__(message)


def _should_retry(exc: BaseException) -> bool:
    """Only retry retriable AIClientError instances."""
    return isinstance(exc, AIClientError) and exc.retriable


class AIClient:
    """Abstraction over Google Generative AI with retry, timeout, and structured output.

    This client never exposes the underlying SDK directly to business logic.
    Gemini is an optional enhancement — all callers must handle AIClientError gracefully
    and fall back to deterministic analysis.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = DEFAULT_MODEL,
        max_retries: int = 2,
        timeout_seconds: int = 45,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or DEFAULT_MODEL
        self._max_retries = max(1, min(max_retries, 5))  # clamp 1-5
        self._timeout_seconds = timeout_seconds
        self._model = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of the AI model."""
        if self._initialized:
            return

        if not self._api_key or self._api_key in ("", "your_api_key_here", "test-key-not-real"):
            raise AIClientError(
                "Google API key is not configured. Set GOOGLE_API_KEY in your .env file.",
                retriable=False,
            )

        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self._model_name)
            self._initialized = True
            logger.info("ai_client_initialized", model=self._model_name)
        except ImportError as exc:
            raise AIClientError(
                "google-generativeai package is not installed.",
                retriable=False,
            ) from exc
        except Exception as exc:
            logger.error("ai_client_init_failed", error=str(exc))
            raise AIClientError(
                "Failed to initialize AI client. Check your API key and network connectivity.",
                retriable=False,
            ) from exc

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Generate text from the AI model.

        Args:
            prompt: The user/document prompt.
            system_instruction: System-level instructions.

        Returns:
            Raw text response from the model.

        Raises:
            AIClientError: On API failure (retriable=False means do NOT retry).
        """
        self._ensure_initialized()

        try:
            generation_config = {
                "temperature": 0.1,  # Lower temp for more consistent, factual output
                "max_output_tokens": 8192,
            }

            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

            response = self._model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            if not response or not response.text:
                raise AIClientError("Empty response from AI model", retriable=True)

            return response.text

        except AIClientError:
            raise
        except Exception as exc:
            error_msg = str(exc)
            # 429 = quota/rate limit, 500/503 = transient server errors
            retriable = any(
                code in error_msg for code in ("429", "500", "503", "RESOURCE_EXHAUSTED")
            )
            logger.error(
                "ai_generation_failed",
                error=error_msg[:200],  # Never log full content (may contain PII)
                retriable=retriable,
            )
            raise AIClientError(
                _user_facing_error(error_msg),
                retriable=retriable,
            ) from exc

    def generate_json(self, prompt: str, system_instruction: str = "") -> dict[str, Any]:
        """Generate and parse a JSON response from the AI model.

        Returns:
            Parsed JSON dictionary.

        Raises:
            AIClientError: On API or parsing failure.
        """
        raw = self.generate(prompt, system_instruction)
        return parse_json_response(raw)

    @property
    def is_configured(self) -> bool:
        """Return True if a valid API key appears to be set."""
        return bool(
            self._api_key and self._api_key not in ("", "your_api_key_here", "test-key-not-real")
        )


def _user_facing_error(raw_error: str) -> str:
    """Convert raw SDK error message to a user-friendly message.

    Never exposes internal paths, keys, or stack traces.
    """
    raw_lower = raw_error.lower()
    if "429" in raw_error or "quota" in raw_lower or "resource_exhausted" in raw_lower:
        return (
            "The AI service quota has been reached. "
            "Document-based fallback analysis is available — please wait before retrying AI features."
        )
    if "api_key" in raw_lower or "api key" in raw_lower or "permission" in raw_lower:
        return "Invalid or missing AI API key. Check GOOGLE_API_KEY in your .env file."
    if "timeout" in raw_lower or "deadline" in raw_lower:
        return "The AI request timed out. The document may be very large — fallback analysis is available."
    if "503" in raw_error or "unavailable" in raw_lower:
        return "The AI service is temporarily unavailable. Fallback analysis is being used."
    return "AI analysis is temporarily unavailable. Document-based fallback analysis is active."


def parse_json_response(raw: str) -> dict[str, Any]:
    """Extract and parse JSON from model response text.

    Handles markdown code fences and other wrapping.
    """
    text = raw.strip()

    # Remove markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if not isinstance(result, dict):
            raise AIClientError("AI response is not a JSON object", retriable=False)
        return result
    except json.JSONDecodeError as exc:
        # Try to find JSON within the text
        json_match = _find_json_in_text(text)
        if json_match is not None:
            return json_match

        logger.error("json_parse_failed", raw_preview=text[:200])
        raise AIClientError(
            "Failed to parse AI response as structured data",
            retriable=False,
        ) from exc


def _find_json_in_text(text: str) -> dict[str, Any] | None:
    """Attempt to find and extract a JSON object from text."""
    # Find the first { and last }
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None

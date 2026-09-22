"""LegalLens AI — AI client abstraction with retry and structured output."""

from __future__ import annotations

import json
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class AIClientError(Exception):
    """Raised when the AI client encounters an error."""

    def __init__(self, message: str, retriable: bool = False) -> None:
        self.retriable = retriable
        super().__init__(message)


class AIClient:
    """Abstraction over Google Generative AI with retry, timeout, and structured output.

    This client never exposes the underlying SDK directly to business logic.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.6-flash",
        max_retries: int = 3,
        timeout_seconds: int = 60,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._model = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of the AI model."""
        if self._initialized:
            return

        if not self._api_key or self._api_key == "your_api_key_here":
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
        except Exception as exc:
            logger.error("ai_client_init_failed", error=str(exc))
            raise AIClientError(
                "Failed to initialize AI client. Check your API key and network.",
                retriable=False,
            ) from exc

    @retry(
        retry=retry_if_exception_type(AIClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
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
            AIClientError: On API failure.
        """
        self._ensure_initialized()

        try:
            generation_config = {
                "temperature": 0.2,
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
            retriable = "429" in error_msg or "500" in error_msg or "503" in error_msg
            logger.error("ai_generation_failed", error=error_msg, retriable=retriable)
            raise AIClientError(
                error_msg,
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
            "Failed to parse AI response as JSON",
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

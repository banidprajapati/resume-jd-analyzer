"""
Thin wrapper around OpenAI-compatible API (Ollama local endpoint).

Returns both the parsed content and token usage, so BudgetEnforcer.record()
can compute simulated cost from real numbers.
"""

import json
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, OpenAI

from resume_agent.core.config import settings

MODEL_NAME = settings.LLM_MODEL
BASE_URL = settings.LLM_BASE_URL


@dataclass
class LLMCallResult:
    raw_text: str
    prompt_tokens: int
    completion_tokens: int

    def as_json(self) -> dict:
        """Parse JSON from LLM output, stripping code fences defensively."""
        text = self.raw_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            return {"_parse_error": str(e), "_raw": self.raw_text}


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key="ollama")
    return _client


def call_llm(
    system_prompt: str, user_prompt: str, force_json: bool = True
) -> LLMCallResult:
    """
    Single synchronous call to the local model via OpenAI-compatible API.

    Args:
        system_prompt: System message content.
        user_prompt: User message content.
        force_json: If True, requests JSON output from the model.

    Returns:
        LLMCallResult with raw text and token counts.

    Raises:
        RuntimeError: On connection or API errors.
    """
    client = _get_client()

    kwargs = {}
    if force_json:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            **kwargs,
        )
    except APIConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Ollama at {BASE_URL}. Is it running? Error: {e}"
        ) from e
    except APIStatusError as e:
        if e.status_code == 404:
            raise RuntimeError(
                f"Model '{MODEL_NAME}' not found. Run 'ollama pull {MODEL_NAME}' first."
            ) from e
        raise RuntimeError(f"Ollama API error: {e}") from e

    choice = response.choices[0]
    usage = response.usage

    return LLMCallResult(
        raw_text=choice.message.content or "",
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )

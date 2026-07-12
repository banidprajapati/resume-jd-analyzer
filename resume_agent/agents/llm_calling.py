"""
Thin wrapper around OpenAI-compatible API (Ollama local endpoint).

Returns both the parsed content and token usage, so BudgetEnforcer.record()
can compute simulated cost from real numbers.
"""

import json
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, OpenAI

from resume_agent.core.config import settings

_client: OpenAI | None = None


def init_client():
    global _client
    _client = OpenAI(base_url=settings.LLM_BASE_URL, api_key="ollama")


@dataclass
class LLMCallResult:
    raw_text: str
    prompt_tokens: int
    completion_tokens: int

    def as_json(self) -> dict:
        text = self.raw_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            return {"_parse_error": str(e), "_raw": self.raw_text}


def call_llm(
    system_prompt: str, user_prompt: str, force_json: bool = True
) -> LLMCallResult:
    kwargs = {}
    if force_json:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = _client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            **kwargs,
        )
    except APIConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Ollama at {settings.LLM_BASE_URL}. Is it running? Error: {e}"
        ) from e
    except APIStatusError as e:
        if e.status_code == 404:
            raise RuntimeError(
                f"Model '{settings.LLM_MODEL}' not found. Run 'ollama pull {settings.LLM_MODEL}' first."
            ) from e
        raise RuntimeError(f"Ollama API error: {e}") from e

    choice = response.choices[0]
    usage = response.usage

    return LLMCallResult(
        raw_text=choice.message.content or "",
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )

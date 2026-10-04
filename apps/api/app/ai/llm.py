from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.ai.errors import AINotConfigured, AIProviderError
from app.core.config import Settings, settings as default_settings


@dataclass
class LLMResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""
    finish_reason: str | None = None


class LLMGateway:
    """Provider-agnostic chat client for any OpenAI-compatible /chat/completions API."""

    def __init__(self, *, api_key: str, model: str, base_url: str, temperature: float = 0.2,
                 max_tokens: int = 1000, timeout: float = 30.0, provider: str = "",
                 transport: httpx.AsyncBaseTransport | None = None):
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")
        self.temperature, self.max_tokens, self.timeout = temperature, max_tokens, timeout
        self.provider = provider or "llm"
        self._transport = transport

    @classmethod
    def from_settings(cls, s: Settings = default_settings) -> "LLMGateway":
        return cls(api_key=s.llm_api_key, model=s.llm_model, base_url=s.llm_base_url,
                   temperature=s.llm_temperature, max_tokens=s.llm_max_tokens,
                   timeout=s.llm_timeout, provider=s.llm_provider)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None,
                   model: str | None = None, temperature: float | None = None,
                   max_tokens: int | None = None) -> LLMResult:
        if not self.configured:
            raise AINotConfigured("Set LLM_API_KEY and LLM_MODEL (and LLM_BASE_URL if not OpenAI).")
        body: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if tools:
            body["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=body,
                                         headers={"Authorization": f"Bearer {self.api_key}"})
        except httpx.HTTPError as exc:
            raise AIProviderError(f"{self.provider} request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise AIProviderError(f"{self.provider} returned {resp.status_code}: {resp.text[:300]}")
        try:
            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
        except (ValueError, KeyError, IndexError) as exc:
            raise AIProviderError(f"{self.provider} returned an unexpected response shape") from exc
        return LLMResult(content=msg.get("content") or "", tool_calls=msg.get("tool_calls") or [],
                         usage=data.get("usage") or {}, model=data.get("model", body["model"]),
                         finish_reason=choice.get("finish_reason"))

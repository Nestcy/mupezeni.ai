"""Provider-agnostic LLM client for any OpenAI-compatible /chat/completions API.

Key features added in Phase 0:
  • reasoning_effort passthrough (Groq qwen3 preview param)
  • extra_params dict for arbitrary provider-specific body keys
  • Automatic fallback to llm_fallback_model on 429 / 503
  • budget_guard hook: a callable that raises if the business is over-budget
  • finish_reason and usage always populated on success
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from app.ai.errors import AINotConfigured, AIProviderError
from app.core.config import Settings, settings as default_settings

logger = logging.getLogger("mupezeni.llm")

# HTTP status codes on which we fall back to the secondary model instead of failing
_FALLBACK_STATUSES = {429, 503}


@dataclass
class LLMResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""
    finish_reason: str | None = None
    fallback_used: bool = False


class LLMGateway:
    """Provider-agnostic chat client for any OpenAI-compatible /chat/completions API.

    Usage with Groq::

        gw = LLMGateway(
            api_key=os.environ["GROQ_API_KEY"],
            model="qwen/qwen3.8-27b",
            base_url="https://api.groq.com/openai/v1",
            fallback_model="llama-3.3-70b-versatile",
            default_reasoning_effort="none",
        )
        result = await gw.chat(messages, reasoning_effort="low")
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        timeout: float = 30.0,
        provider: str = "",
        fallback_model: str = "",
        default_reasoning_effort: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.provider = provider or "llm"
        self.fallback_model = fallback_model
        self.default_reasoning_effort = default_reasoning_effort
        self._transport = transport

    @classmethod
    def from_settings(cls, s: Settings = default_settings) -> "LLMGateway":
        return cls(
            api_key=s.llm_api_key,
            model=s.llm_model,
            base_url=s.llm_base_url,
            temperature=s.llm_temperature,
            max_tokens=s.llm_max_tokens,
            timeout=s.llm_timeout,
            provider=s.llm_provider,
            fallback_model=s.llm_fallback_model,
            default_reasoning_effort=s.llm_reasoning_effort,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
        extra_params: dict[str, Any] | None = None,
        budget_guard: Callable[[], None] | None = None,
    ) -> LLMResult:
        """Send a chat request.

        Args:
            messages: OpenAI-format message list.
            tools: OpenAI tool schemas (function definitions).
            model: Override the instance model for this call.
            temperature: Override instance temperature.
            max_tokens: Override instance max_tokens.
            reasoning_effort: Groq/provider-specific reasoning level
                (``"none"`` | ``"low"`` | ``"medium"`` | ``"high"``).
                Defaults to ``self.default_reasoning_effort``; pass ``""`` to suppress.
            extra_params: Arbitrary keys merged into the request body after all
                standard params — for provider-specific extensions.
            budget_guard: Called before the HTTP request is made.  Raise any
                exception here to abort the call (e.g. daily budget exceeded).

        Returns:
            LLMResult with content, tool_calls, usage, model, finish_reason.

        Raises:
            AINotConfigured: API key / model not set.
            AIProviderError: Provider returned an error or bad response shape.
        """
        if not self.configured:
            raise AINotConfigured(
                "Set LLM_API_KEY and LLM_MODEL (and LLM_BASE_URL if not OpenAI)."
            )

        if budget_guard is not None:
            budget_guard()

        primary_model = model or self.model
        body = self._build_body(
            messages=messages,
            model=primary_model,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            extra_params=extra_params,
        )

        try:
            return await self._post(body, fallback_used=False)
        except AIProviderError as exc:
            # Attempt fallback on retriable statuses if a fallback model is configured
            if self.fallback_model and exc.status_code in _FALLBACK_STATUSES:
                logger.warning(
                    "Primary model %s returned %s; falling back to %s",
                    primary_model,
                    exc.status_code,
                    self.fallback_model,
                )
                fallback_body = self._build_body(
                    messages=messages,
                    model=self.fallback_model,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    # Fallback model may not support reasoning_effort — omit it
                    reasoning_effort=None,
                    extra_params=extra_params,
                )
                result = await self._post(fallback_body, fallback_used=True)
                return result
            raise

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_body(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        temperature: float | None,
        max_tokens: int | None,
        reasoning_effort: str | None,
        extra_params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if tools:
            body["tools"] = tools
        # Apply reasoning_effort: use argument if provided; else fall back to instance default;
        # empty string means "suppress" (don't send the param at all).
        effort = reasoning_effort if reasoning_effort is not None else self.default_reasoning_effort
        if effort:
            body["reasoning_effort"] = effort
        if extra_params:
            body.update(extra_params)
        return body

    async def _post(self, body: dict[str, Any], *, fallback_used: bool) -> LLMResult:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, transport=self._transport
            ) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except httpx.HTTPError as exc:
            raise AIProviderError(f"{self.provider} request failed: {exc}") from exc

        if resp.status_code >= 400:
            err = AIProviderError(
                f"{self.provider} returned {resp.status_code}: {resp.text[:300]}"
            )
            err.status_code = resp.status_code  # type: ignore[attr-defined]
            raise err

        try:
            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
        except (ValueError, KeyError, IndexError) as exc:
            raise AIProviderError(
                f"{self.provider} returned an unexpected response shape"
            ) from exc

        return LLMResult(
            content=msg.get("content") or "",
            tool_calls=msg.get("tool_calls") or [],
            usage=data.get("usage") or {},
            model=data.get("model", body["model"]),
            finish_reason=choice.get("finish_reason"),
            fallback_used=fallback_used,
        )

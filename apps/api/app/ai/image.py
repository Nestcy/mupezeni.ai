"""Image generation client — supports two protocols:

  "openai"  (default)
    POST {image_base_url}/images/generations
    Request:  {"model": ..., "prompt": ..., "n": ..., "size": ...}
    Response: {"data": [{"url": ..., "b64_json": ..., "revised_prompt": ...}]}

  "gemini"
    POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}
    Request:  {"contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}
    Response: candidates[0].content.parts  — each part has either
              .text  or  .inlineData.{mimeType, data}  (base64)

Select with IMAGE_PROTOCOL env var (or image_protocol in Settings).
Model for Gemini: gemini-3.1-flash-lite-image  (1 K images; preview as of Oct 2026).
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.ai.errors import AINotConfigured, AIProviderError
from app.core.config import Settings, settings as default_settings

logger = logging.getLogger("mupezeni.image")

# Gemini base URL — key is a query param, not a header
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass
class ImageResult:
    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None
    mime_type: str = "image/png"


# ── OpenAI-compatible adapter ──────────────────────────────────────────────────

class _OpenAIImageClient:
    """Calls any OpenAI-compatible /images/generations endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        size: str = "1024x1024",
        timeout: float = 120.0,
        provider: str = "image",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.size = size
        self.timeout = timeout
        self.provider = provider
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, prompt: str, *, size: str | None = None, n: int = 1) -> list[ImageResult]:
        if not self.configured:
            raise AINotConfigured(
                "Set IMAGE_API_KEY and IMAGE_MODEL (and IMAGE_BASE_URL if not OpenAI)."
            )
        body: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "n": n,
            "size": size or self.size,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                resp = await client.post(
                    f"{self.base_url}/images/generations",
                    json=body,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except httpx.HTTPError as exc:
            raise AIProviderError(f"{self.provider} request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise AIProviderError(
                f"{self.provider} returned {resp.status_code}: {resp.text[:300]}"
            )
        try:
            items = resp.json()["data"]
        except (ValueError, KeyError) as exc:
            raise AIProviderError(
                f"{self.provider} returned an unexpected response shape"
            ) from exc
        return [
            ImageResult(
                url=i.get("url"),
                b64_json=i.get("b64_json"),
                revised_prompt=i.get("revised_prompt"),
            )
            for i in items
        ]


# ── Gemini adapter ─────────────────────────────────────────────────────────────

class _GeminiImageClient:
    """Calls the Gemini generateContent API for image generation.

    Verified against:
      https://ai.google.dev/api/generate-content
      Model: gemini-3.1-flash-lite-image (IMAGE_MODEL env var)

    The response contains parts with inlineData.  We return b64_json so the
    caller can upload to Supabase Storage and return a URL.  Only 1 image per
    request (n is ignored; Gemini does not support n > 1 for image generation).
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        provider: str = "gemini-image",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.provider = provider
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, prompt: str, *, size: str | None = None, n: int = 1) -> list[ImageResult]:
        if not self.configured:
            raise AINotConfigured(
                "Set IMAGE_API_KEY and IMAGE_MODEL for Gemini image generation."
            )
        if n > 1:
            logger.warning(
                "Gemini image adapter does not support n>1 (got n=%d); generating 1 image.", n
            )

        url = f"{_GEMINI_BASE}/{self.model}:generateContent"
        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
            },
        }
        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                resp = await client.post(url, json=body, params=params)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"{self.provider} request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise AIProviderError(
                f"{self.provider} returned {resp.status_code}: {resp.text[:400]}"
            )

        try:
            data = resp.json()
            parts: list[dict[str, Any]] = (
                data["candidates"][0]["content"]["parts"]
            )
        except (ValueError, KeyError, IndexError) as exc:
            raise AIProviderError(
                f"{self.provider} returned an unexpected response shape"
            ) from exc

        results: list[ImageResult] = []
        for part in parts:
            if "inlineData" in part:
                inline = part["inlineData"]
                results.append(
                    ImageResult(
                        b64_json=inline.get("data"),
                        mime_type=inline.get("mimeType", "image/png"),
                    )
                )
            # TEXT parts (revised prompt / captions) are ignored here
        if not results:
            raise AIProviderError(
                f"{self.provider} response contained no image parts.  "
                "Check that responseModalities includes 'IMAGE'."
            )
        return results


# ── Public facade ──────────────────────────────────────────────────────────────

class ImageClient:
    """Factory that selects the correct adapter based on IMAGE_PROTOCOL.

    Use ``ImageClient.from_settings()`` to get an instance configured from
    environment variables.  The returned object exposes:

        async def generate(prompt, *, size=None, n=1) -> list[ImageResult]
        @property configured: bool
    """

    def __new__(  # type: ignore[misc]
        cls,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        size: str = "1024x1024",
        timeout: float = 120.0,
        provider: str = "",
        protocol: str = "openai",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> _OpenAIImageClient | _GeminiImageClient:
        if protocol == "gemini":
            return _GeminiImageClient(
                api_key=api_key,
                model=model,
                timeout=timeout,
                provider=provider or "gemini-image",
                transport=transport,
            )
        return _OpenAIImageClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            size=size,
            timeout=timeout,
            provider=provider or "image",
            transport=transport,
        )

    @classmethod
    def from_settings(cls, s: Settings = default_settings) -> _OpenAIImageClient | _GeminiImageClient:
        return cls(  # type: ignore[return-value]
            api_key=s.image_api_key,
            model=s.image_model,
            base_url=s.image_base_url,
            size=s.image_size,
            timeout=s.image_timeout,
            provider=s.image_provider,
            protocol=s.image_protocol,
        )

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.ai.errors import AINotConfigured, AIProviderError
from app.core.config import Settings, settings as default_settings


@dataclass
class ImageResult:
    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None


class ImageClient:
    """Provider-agnostic image generation via an OpenAI-compatible /images/generations API."""

    def __init__(self, *, api_key: str, model: str, base_url: str, size: str = "1024x1024",
                 timeout: float = 120.0, provider: str = "",
                 transport: httpx.AsyncBaseTransport | None = None):
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")
        self.size, self.timeout = size, timeout
        self.provider = provider or "image"
        self._transport = transport

    @classmethod
    def from_settings(cls, s: Settings = default_settings) -> "ImageClient":
        return cls(api_key=s.image_api_key, model=s.image_model, base_url=s.image_base_url,
                   size=s.image_size, timeout=s.image_timeout, provider=s.image_provider)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, prompt: str, *, size: str | None = None, n: int = 1) -> list[ImageResult]:
        if not self.configured:
            raise AINotConfigured("Set IMAGE_API_KEY and IMAGE_MODEL (and IMAGE_BASE_URL if not OpenAI).")
        body = {"model": self.model, "prompt": prompt, "n": n, "size": size or self.size}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                resp = await client.post(f"{self.base_url}/images/generations", json=body,
                                         headers={"Authorization": f"Bearer {self.api_key}"})
        except httpx.HTTPError as exc:
            raise AIProviderError(f"{self.provider} request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise AIProviderError(f"{self.provider} returned {resp.status_code}: {resp.text[:300]}")
        try:
            items = resp.json()["data"]
        except (ValueError, KeyError) as exc:
            raise AIProviderError(f"{self.provider} returned an unexpected response shape") from exc
        return [ImageResult(url=i.get("url"), b64_json=i.get("b64_json"),
                            revised_prompt=i.get("revised_prompt")) for i in items]

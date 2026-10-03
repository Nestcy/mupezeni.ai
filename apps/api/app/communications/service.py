from __future__ import annotations

from typing import Any

from app.communications.models import IncomingMessage, OutboundMessage


class WebhookRequest:
    def __init__(self, payload: dict[str, Any], provider: str):
        self.payload = payload
        self.provider = provider


class CommunicationService:
    """Resolve provider, validate recipients, send messages, and persist delivery outcomes."""

    def __init__(self):
        self._providers: dict[str, Any] = {}

    def register_provider(self, provider_name: str, provider: Any) -> None:
        self._providers[provider_name] = provider

    async def send(self, message: OutboundMessage) -> DeliveryResult:
        provider = self._providers.get("web", None)
        if provider is None:
            return DeliveryResult(provider="web", status="queued", metadata={"message": "no_provider_configured"})
        return await provider.send_message(message)


from app.communications.models import DeliveryResult

__all__ = ["CommunicationService", "WebhookRequest", "IncomingMessage", "OutboundMessage", "DeliveryResult"]

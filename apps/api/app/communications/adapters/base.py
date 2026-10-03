from __future__ import annotations

from typing import Any

from app.communications.models import OutboundMessage, DeliveryResult


class ChannelAdapter:
    """Protocol-like adapter interface for communication providers."""

    async def parse_inbound(self, payload: dict[str, Any]) -> Any:
        raise NotImplementedError

    async def send(self, message: OutboundMessage) -> DeliveryResult:
        raise NotImplementedError


class WebChannelAdapter(ChannelAdapter):
    """Simple testable web channel adapter."""

    async def parse_inbound(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    async def send(self, message: OutboundMessage) -> DeliveryResult:
        return DeliveryResult(provider="web", status="queued", external_message_id=message.conversation_id)


__all__ = ["ChannelAdapter", "WebChannelAdapter"]

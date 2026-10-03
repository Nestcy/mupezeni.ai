from __future__ import annotations

from typing import Any

from app.communications.models import OutboundMessage, DeliveryResult


class CommunicationProvider:
    """Provider contract for sending outbound messages."""

    async def send_message(self, message: OutboundMessage) -> DeliveryResult:
        raise NotImplementedError


class WebCommunicationProvider(CommunicationProvider):
    """Internal provider for web chat. No external credentials required."""

    async def send_message(self, message: OutboundMessage) -> DeliveryResult:
        return DeliveryResult(
            provider="web",
            status="sent",
            external_message_id=f"web_{message.conversation_id}",
            metadata={"recipient": message.recipient, "content": message.content},
        )


__all__ = ["CommunicationProvider", "WebCommunicationProvider"]

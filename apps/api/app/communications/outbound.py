from __future__ import annotations

from typing import Any

from app.communications.models import OutboundMessage, DeliveryResult


class OutboundMessageHandler:
    """Minimal outbound message handler for conversation responses."""

    async def send(self, provider: str, message: OutboundMessage) -> DeliveryResult:
        return DeliveryResult(provider=provider, status="sent", external_message_id=f"msg_{message.conversation_id}", metadata={"content": message.content})


__all__ = ["OutboundMessageHandler"]

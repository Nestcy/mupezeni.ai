from __future__ import annotations

from typing import Any

from app.communications.models import IncomingMessage, OutboundMessage, DeliveryResult


class InboundMessageNormalizer:
    """Normalize provider payloads to internal message contract."""

    def normalize(self, provider: str, payload: dict[str, Any]) -> IncomingMessage:
        return IncomingMessage(
            business_id=payload.get("business_id", "biz_123"),
            channel=provider,
            external_message_id=str(payload.get("message_id") or payload.get("external_message_id") or "ext_001"),
            customer_identity=payload.get("customer_identity"),
            conversation_identity=payload.get("conversation_identity"),
            message_type=payload.get("message_type", "text"),
            content=str(payload.get("content") or ""),
            received_at=payload.get("received_at"),
        )


class OutboundMessageNormalizer:
    """Normalize internal outbound messages for channel providers."""

    def normalize(self, outbound: OutboundMessage) -> dict[str, Any]:
        return {
            "business_id": outbound.business_id,
            "conversation_id": outbound.conversation_id,
            "recipient": outbound.recipient,
            "message_type": outbound.message_type,
            "content": outbound.content,
            "metadata": outbound.metadata,
        }


__all__ = ["InboundMessageNormalizer", "OutboundMessageNormalizer"]

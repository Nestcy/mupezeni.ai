from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MessageAttachment(BaseModel):
    type: str
    url: str | None = None
    storage_path: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeliveryResult(BaseModel):
    provider: str
    status: str = "queued"
    external_message_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutboundMessageEnvelope(BaseModel):
    business_id: str
    conversation_id: str
    recipient: str
    message_type: str = "text"
    content: str
    attachments: list[MessageAttachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncomingMessageEnvelope(BaseModel):
    business_id: str
    channel: str = "web"
    external_message_id: str
    customer_identity: str | None = None
    conversation_identity: str | None = None
    message_type: str = "text"
    content: str
    received_at: str | None = None


__all__ = ["MessageAttachment", "DeliveryResult", "OutboundMessageEnvelope", "IncomingMessageEnvelope"]

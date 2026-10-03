from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationSchema(BaseModel):
    business_id: str
    customer_id: str
    channel: str = "web"
    channel_conversation_id: str | None = None
    status: str = "active"
    assigned_worker: str | None = None
    current_goal: str | None = None
    current_state: str = "browsing"


class MessageSchema(BaseModel):
    conversation_id: str
    business_id: str
    sender_type: str = "customer"
    sender_id: str | None = None
    direction: str = "inbound"
    message_type: str = "text"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    external_message_id: str | None = None


class ConversationContextSchema(BaseModel):
    conversation_id: str
    current_goal: str | None = None
    current_product: str | None = None
    current_variant: str | None = None
    cart_id: str | None = None
    recent_messages: list[str] = Field(default_factory=list)
    state: str = "browsing"


class WebhookEvent(BaseModel):
    provider: str
    payload: dict[str, Any]
    received_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "ConversationSchema",
    "MessageSchema",
    "ConversationContextSchema",
    "WebhookEvent",
]

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    CLOSED = "closed"
    ARCHIVED = "archived"


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    LOCATION = "location"
    INTERACTIVE = "interactive"
    SYSTEM = "system"


class ConversationState(str, Enum):
    BROWSING = "browsing"
    PRODUCT_SELECTION = "product_selection"
    VARIANT_SELECTION = "variant_selection"
    CART_BUILDING = "cart_building"
    CHECKOUT_READY = "checkout_ready"
    WAITING = "waiting"
    HANDOFF = "handoff"
    CLOSED = "closed"


class Conversation(BaseModel):
    id: str
    business_id: str
    customer_id: str
    channel: str = "web"
    channel_conversation_id: str | None = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    assigned_worker: str | None = None
    current_goal: str | None = None
    current_state: ConversationState = ConversationState.BROWSING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = None


class Message(BaseModel):
    id: str
    conversation_id: str
    business_id: str
    sender_type: str = "customer"
    sender_id: str | None = None
    direction: MessageDirection = MessageDirection.INBOUND
    message_type: MessageType = MessageType.TEXT
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    external_message_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IncomingMessage(BaseModel):
    business_id: str
    channel: str = "web"
    external_message_id: str
    customer_identity: str | None = None
    conversation_identity: str | None = None
    message_type: str = "text"
    content: str
    received_at: datetime = Field(default_factory=datetime.utcnow)


class OutboundMessage(BaseModel):
    business_id: str
    conversation_id: str
    recipient: str
    message_type: str = "text"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class MessageDelivery(BaseModel):
    id: str
    message_id: str
    provider: str = "web"
    external_message_id: str | None = None
    status: DeliveryStatus = DeliveryStatus.QUEUED
    error_code: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    conversation_id: str
    current_goal: str | None = None
    current_product: str | None = None
    current_variant: str | None = None
    cart_id: str | None = None
    recent_messages: list[str] = Field(default_factory=list)
    last_tool: str | None = None
    last_action: str | None = None
    state: ConversationState = ConversationState.BROWSING


__all__ = [
    "Conversation",
    "Message",
    "IncomingMessage",
    "OutboundMessage",
    "ConversationContext",
    "MessageDelivery",
    "ConversationStatus",
    "MessageDirection",
    "MessageType",
    "ConversationState",
    "DeliveryStatus",
]

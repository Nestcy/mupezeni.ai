from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageProcessingStatus(str):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class MessageRecord(BaseModel):
    id: str
    conversation_id: str
    business_id: str
    sender_type: str = "customer"
    sender_id: str | None = None
    direction: str = "inbound"
    message_type: str = "text"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    external_message_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = MessageProcessingStatus.RECEIVED
    retry_count: int = 0
    error_code: str | None = None
    last_error: str | None = None


class ConversationProcessingService:
    """Track message processing and idempotency for a conversation."""

    def __init__(self):
        self._messages: dict[str, MessageRecord] = {}

    def save(self, message: MessageRecord) -> MessageRecord:
        self._messages[message.id] = message
        return message

    def get_by_external_id(self, external_message_id: str) -> MessageRecord | None:
        for record in self._messages.values():
            if record.external_message_id == external_message_id:
                return record
        return None

    def set_status(self, message_id: str, status: str, *, error_code: str | None = None, last_error: str | None = None) -> MessageRecord | None:
        message = self._messages.get(message_id)
        if not message:
            return None
        message.status = status
        message.error_code = error_code
        message.last_error = last_error
        return message


__all__ = ["MessageRecord", "ConversationProcessingService", "MessageProcessingStatus"]

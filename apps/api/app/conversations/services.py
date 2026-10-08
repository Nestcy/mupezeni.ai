from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


from app.db.repositories.conversations import (
    ConversationRepository,
    InMemoryConversationRepository,
)
from app.db.repositories.messages import (
    InMemoryMessageRepository,
    MessageRepository,
)


class ConversationService:
    """Manage conversation lifecycle and state."""

    def __init__(
        self,
        repo: ConversationRepository | None = None,
        message_repo: MessageRepository | None = None,
    ) -> None:
        self.repo = repo or InMemoryConversationRepository()
        self.message_repo = message_repo or InMemoryMessageRepository()
        self._conversations: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}

    def create(self, business_id: str, customer_id: str, channel: str = "web") -> dict[str, Any]:
        conversation_id = f"conv_{len(self._conversations) + 1:06d}"
        item = {
            "id": conversation_id,
            "business_id": business_id,
            "customer_id": customer_id,
            "channel": channel,
            "status": "active",
            "current_state": "browsing",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._conversations[conversation_id] = item
        self._messages[conversation_id] = []

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    self.repo.create(
                        business_id=business_id,
                        customer_id=customer_id,
                        channel=channel,
                    )
                )
        except Exception:
            pass

        return item

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        return self._conversations.get(conversation_id)

    def add_message(self, conversation_id: str, message: dict[str, Any]) -> dict[str, Any]:
        self._messages.setdefault(conversation_id, []).append(message)
        convo = self._conversations.get(conversation_id)
        if convo:
            convo["updated_at"] = datetime.utcnow().isoformat()
            convo["last_message_at"] = datetime.utcnow().isoformat()

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    self.message_repo.create(
                        conversation_id=conversation_id,
                        business_id=convo["business_id"] if convo else "",
                        content=message.get("content", ""),
                        sender_type=message.get("sender_type", "customer"),
                        sender_id=message.get("sender_id"),
                        direction=message.get("direction", "inbound"),
                        metadata=message.get("metadata"),
                    )
                )
        except Exception:
            pass

        return message

    def get_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self._messages.get(conversation_id, []))


class ConversationContextService:
    """Provide recent conversation context to a worker."""

    def build_context(self, conversation_id: str, recent_messages: list[str] | None = None, current_product: str | None = None, cart_id: str | None = None) -> dict[str, Any]:
        recent = recent_messages or []
        return {
            "conversation_id": conversation_id,
            "current_goal": "purchase",
            "current_product": current_product,
            "current_variant": None,
            "cart_id": cart_id,
            "recent_messages": recent[-10:],
            "state": "browsing",
        }


class MessageProcessingQueue:
    """Lightweight queue abstraction for async processing."""

    def __init__(self):
        self._queue: list[str] = []

    async def enqueue(self, message_id: str) -> str:
        self._queue.append(message_id)
        return message_id

    def pending(self) -> list[str]:
        return list(self._queue)


__all__ = ["ConversationService", "ConversationContextService", "MessageProcessingQueue"]

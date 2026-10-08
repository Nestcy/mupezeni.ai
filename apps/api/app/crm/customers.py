from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.repositories.conversation import ConversationRepository


class InMemoryConversationRepository:
    """Fallback repo used in tests and local processes when Supabase is unavailable."""

    def __init__(self):
        self._conversations: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}

    async def create(self, business_id: str, customer_id: str, *, channel: str = "web", status: str = "active") -> dict[str, Any]:
        conversation_id = f"conv_{len(self._conversations) + 1:06d}"
        item = {
            "id": conversation_id,
            "business_id": business_id,
            "customer_id": customer_id,
            "channel": channel,
            "status": status,
            "ai_enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._conversations[conversation_id] = item
        self._messages[conversation_id] = []
        return item

    async def get_by_id(self, conversation_id: str, business_id: str | None = None) -> dict[str, Any] | None:
        convo = self._conversations.get(conversation_id)
        if convo and business_id and convo["business_id"] != business_id:
            return None
        return convo

    async def list_for_business(self, business_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return [c for c in self._conversations.values() if c["business_id"] == business_id][:limit]

    async def add_message(self, conversation_id: str, message: dict[str, Any]) -> dict[str, Any]:
        self._messages.setdefault(conversation_id, []).append(message)
        convo = self._conversations.get(conversation_id)
        if convo:
            convo["updated_at"] = datetime.utcnow().isoformat()
            convo["last_message_at"] = datetime.utcnow().isoformat()
        return message

    async def get_messages(self, conversation_id: str, *, after: str | None = None) -> list[dict[str, Any]]:
        msgs = list(self._messages.get(conversation_id, []))
        if after:
            return [m for m in msgs if m.get("created_at", "") > after]
        return msgs

    async def update_status(self, conversation_id: str, business_id: str, status: str) -> dict[str, Any]:
        convo = self._conversations.get(conversation_id)
        if convo is None or convo["business_id"] != business_id:
            return {}
        convo["status"] = status
        convo["updated_at"] = datetime.utcnow().isoformat()
        return convo


class ConversationService:
    """Manage conversation lifecycle and state."""

    def __init__(self, repository: Any | None = None):
        self._repository = repository or InMemoryConversationRepository()

    async def create(self, business_id: str, customer_id: str, channel: str = "web") -> dict[str, Any]:
        return await self._repository.create(business_id, customer_id, channel=channel)

    async def get(self, conversation_id: str, business_id: str | None = None) -> dict[str, Any] | None:
        return await self._repository.get_by_id(conversation_id, business_id)

    async def add_message(self, conversation_id: str, message: dict[str, Any]) -> dict[str, Any]:
        return await self._repository.add_message(conversation_id, message)

    async def get_messages(self, conversation_id: str, *, after: str | None = None) -> list[dict[str, Any]]:
        return await self._repository.get_messages(conversation_id, after=after)

    async def list_for_business(self, business_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if hasattr(self._repository, "list_for_business"):
            return await self._repository.list_for_business(business_id, limit=limit)
        return []


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


__all__ = ["ConversationService", "ConversationContextService", "MessageProcessingQueue", "InMemoryConversationRepository"]

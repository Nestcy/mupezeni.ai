from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.repositories.conversation import ConversationRepository


class InMemoryCustomerRepository:
    """Fallback repository used in local tests and development when Supabase is not configured."""

    def __init__(self):
        self._customers: dict[str, dict[str, Any]] = {}
        self._interactions: dict[str, dict[str, Any]] = {}

    async def create(self, business_id: str, data: dict[str, Any]) -> dict[str, Any]:
        customer_id = str(data["id"])
        record = {**data, "business_id": business_id}
        record.setdefault("created_at", datetime.utcnow().isoformat())
        record.setdefault("updated_at", datetime.utcnow().isoformat())
        self._customers[customer_id] = record
        return record

    async def get_by_id(self, business_id: str, customer_id: str) -> dict[str, Any] | None:
        item = self._customers.get(customer_id)
        if item is None:
            return None
        if item.get("business_id") != business_id:
            return None
        return item

    async def list_for_business(self, business_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [item for item in self._customers.values() if item.get("business_id") == business_id][:limit]

    async def add_interaction(self, business_id: str, interaction: dict[str, Any]) -> dict[str, Any]:
        item = {**interaction, "business_id": business_id}
        item.setdefault("occurred_at", datetime.utcnow().isoformat())
        self._interactions[item["id"]] = item
        return item

    async def list_for_customer(self, customer_id: str) -> list[dict[str, Any]]:
        return [item for item in self._interactions.values() if item.get("customer_id") == customer_id]


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


class CustomerManagementService:
    """Manage customer records with an injected repository, defaulting to in-memory storage for tests."""

    def __init__(self, repository: Any | None = None):
        self._repository = repository or InMemoryCustomerRepository()

    async def create(self, customer: Any) -> Any:
        if hasattr(self._repository, "create"):
            repo_customer = await self._repository.create(customer.business_id, customer.model_dump())
            if isinstance(repo_customer, dict):
                return customer.__class__(**repo_customer)
            return repo_customer
        self._repository._customers[customer.id] = customer.model_dump()
        return customer

    async def get(self, customer_id: str, business_id: str | None = None) -> Any | None:
        if hasattr(self._repository, "get_by_id"):
            item = await self._repository.get_by_id(business_id or "", customer_id)
            if item is None:
                return None
            return item
        customer = self._repository._customers.get(customer_id)
        if customer and business_id and customer.get("business_id") != business_id:
            return None
        return customer

    async def list_for_business(self, business_id: str) -> list[Any]:
        if hasattr(self._repository, "list_for_business"):
            return await self._repository.list_for_business(business_id)
        return [customer for customer in self._repository._customers.values() if customer.get("business_id") == business_id]


class CustomerInteractionService:
    """Lightweight customer interaction history support."""

    def __init__(self, repository: Any | None = None):
        self._repository = repository or InMemoryCustomerRepository()

    async def record(self, interaction: Any) -> Any:
        if hasattr(self._repository, "add_interaction"):
            item = await self._repository.add_interaction(interaction.business_id or "", interaction.model_dump())
            return interaction.__class__(**item) if isinstance(item, dict) else item
        self._repository._interactions[interaction.id] = interaction.model_dump()
        return interaction

    async def list_for_customer(self, customer_id: str) -> list[Any]:
        if hasattr(self._repository, "list_for_customer"):
            return await self._repository.list_for_customer(customer_id)
        return [interaction for interaction in self._repository._interactions.values() if interaction.get("customer_id") == customer_id]


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


__all__ = [
    "CustomerManagementService",
    "CustomerInteractionService",
    "ConversationService",
    "InMemoryCustomerRepository",
    "InMemoryConversationRepository",
]

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class MessageRepository(Protocol):
    async def create(
        self,
        conversation_id: str,
        business_id: str,
        content: str,
        sender_type: str = "customer",
        sender_id: str | None = None,
        direction: str = "inbound",
        message_type: str = "text",
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "delivered",
    ) -> dict[str, Any]: ...

    async def list_by_conversation(
        self, conversation_id: str, limit: int = 50, after: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def get_by_id(self, message_id: str) -> dict[str, Any] | None: ...

    async def update_status_by_external_id(
        self, external_message_id: str, status: str
    ) -> bool: ...


class SupabaseMessageRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self,
        conversation_id: str,
        business_id: str,
        content: str,
        sender_type: str = "customer",
        sender_id: str | None = None,
        direction: str = "inbound",
        message_type: str = "text",
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "delivered",
    ) -> dict[str, Any]:
        data = {
            "conversation_id": conversation_id,
            "business_id": business_id,
            "content": content,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "direction": direction,
            "message_type": message_type,
            "external_message_id": external_message_id,
            "metadata": metadata or {},
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("messages").insert(data).execute()
        return res.data[0] if res.data else data

    async def list_by_conversation(
        self, conversation_id: str, limit: int = 50, after: str | None = None
    ) -> list[dict[str, Any]]:
        q = (
            self._client()
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(limit)
        )
        if after:
            q = q.gt("created_at", after)
        res = q.execute()
        return res.data or []

    async def get_by_id(self, message_id: str) -> dict[str, Any] | None:
        res = self._client().table("messages").select("*").eq("id", message_id).execute()
        return res.data[0] if res.data else None

    async def update_status_by_external_id(
        self, external_message_id: str, status: str
    ) -> bool:
        res = (
            self._client()
            .table("messages")
            .update({"status": status})
            .eq("external_message_id", external_message_id)
            .execute()
        )
        return bool(res.data)


class InMemoryMessageRepository:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def create(
        self,
        conversation_id: str,
        business_id: str,
        content: str,
        sender_type: str = "customer",
        sender_id: str | None = None,
        direction: str = "inbound",
        message_type: str = "text",
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "delivered",
    ) -> dict[str, Any]:
        item = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "business_id": business_id,
            "content": content,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "direction": direction,
            "message_type": message_type,
            "external_message_id": external_message_id,
            "metadata": metadata or {},
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.messages.append(item)
        return item

    async def list_by_conversation(
        self, conversation_id: str, limit: int = 50, after: str | None = None
    ) -> list[dict[str, Any]]:
        filtered = [
            m for m in self.messages if m["conversation_id"] == conversation_id
        ]
        if after:
            filtered = [m for m in filtered if m["created_at"] > after]
        filtered.sort(key=lambda x: x["created_at"])
        return filtered[:limit]

    async def get_by_id(self, message_id: str) -> dict[str, Any] | None:
        for m in self.messages:
            if m["id"] == message_id:
                return m
        return None

    async def update_status_by_external_id(
        self, external_message_id: str, status: str
    ) -> bool:
        updated = False
        for m in self.messages:
            if m.get("external_message_id") == external_message_id:
                m["status"] = status
                updated = True
        return updated

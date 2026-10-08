from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class ConversationRepository(Protocol):
    async def create(
        self,
        business_id: str,
        customer_id: str,
        channel: str = "web",
        channel_conversation_id: str | None = None,
        status: str = "active",
        current_state: str = "browsing",
    ) -> dict[str, Any]: ...

    async def get(
        self, conversation_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def list_for_business(
        self,
        business_id: str,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def update(
        self, conversation_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    async def set_ai_state(
        self, conversation_id: str, ai_enabled: bool, ai_paused_by: str | None = None
    ) -> dict[str, Any] | None: ...


class SupabaseConversationRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self,
        business_id: str,
        customer_id: str,
        channel: str = "web",
        channel_conversation_id: str | None = None,
        status: str = "active",
        current_state: str = "browsing",
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "customer_id": customer_id,
            "channel": channel,
            "channel_conversation_id": channel_conversation_id,
            "status": status,
            "current_state": current_state,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("conversations").insert(data).execute()
        return res.data[0] if res.data else data

    async def get(
        self, conversation_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("conversations").select("*").eq("id", conversation_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def list_for_business(
        self,
        business_id: str,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        q = (
            self._client()
            .table("conversations")
            .select("*")
            .eq("business_id", business_id)
            .order("updated_at", desc=True)
            .limit(limit)
        )
        if status:
            q = q.eq("status", status)
        if channel:
            q = q.eq("channel", channel)
        if cursor:
            q = q.lt("updated_at", cursor)
        res = q.execute()
        return res.data or []

    async def update(
        self, conversation_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = (
            self._client()
            .table("conversations")
            .update(updates)
            .eq("id", conversation_id)
            .execute()
        )
        return res.data[0] if res.data else None

    async def set_ai_state(
        self, conversation_id: str, ai_enabled: bool, ai_paused_by: str | None = None
    ) -> dict[str, Any] | None:
        return await self.update(
            conversation_id, {"ai_enabled": ai_enabled, "ai_paused_by": ai_paused_by}
        )


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.conversations: dict[str, dict[str, Any]] = {}

    async def create(
        self,
        business_id: str,
        customer_id: str,
        channel: str = "web",
        channel_conversation_id: str | None = None,
        status: str = "active",
        current_state: str = "browsing",
    ) -> dict[str, Any]:
        cid = str(uuid.uuid4())
        item = {
            "id": cid,
            "business_id": business_id,
            "customer_id": customer_id,
            "channel": channel,
            "channel_conversation_id": channel_conversation_id,
            "status": status,
            "current_state": current_state,
            "ai_enabled": True,
            "ai_paused_by": None,
            "unread_count": 0,
            "last_customer_message_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.conversations[cid] = item
        return item

    async def get(
        self, conversation_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        item = self.conversations.get(conversation_id)
        if item and business_id and item["business_id"] != business_id:
            return None
        return item

    async def list_for_business(
        self,
        business_id: str,
        status: str | None = None,
        channel: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        results = [
            c for c in self.conversations.values() if c["business_id"] == business_id
        ]
        if status:
            results = [c for c in results if c.get("status") == status]
        if channel:
            results = [c for c in results if c.get("channel") == channel]
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results[:limit]

    async def update(
        self, conversation_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        item = self.conversations.get(conversation_id)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
        return item

    async def set_ai_state(
        self, conversation_id: str, ai_enabled: bool, ai_paused_by: str | None = None
    ) -> dict[str, Any] | None:
        return await self.update(
            conversation_id, {"ai_enabled": ai_enabled, "ai_paused_by": ai_paused_by}
        )

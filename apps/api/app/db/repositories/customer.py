from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class ConversationRepository:
    """Supabase-backed repository for conversations and messages."""

    @staticmethod
    async def create(business_id: str, customer_id: str, *, channel: str = "web", status: str = "active") -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("conversations")
            .insert({
                "business_id": business_id,
                "customer_id": customer_id,
                "channel": channel,
                "status": status,
                "ai_enabled": True,
            })
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(conversation_id: str, business_id: str | None = None) -> dict[str, Any] | None:
        client = get_database_client()
        query = client.table("conversations").select("*").eq("id", conversation_id)
        if business_id:
            query = query.eq("business_id", business_id)
        result = query.single().execute()
        return result.data if result.data else None

    @staticmethod
    async def list_for_business(business_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("conversations")
            .select("*")
            .eq("business_id", business_id)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def add_message(conversation_id: str, message: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = client.table("messages").insert(message).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_messages(conversation_id: str, *, after: str | None = None) -> list[dict[str, Any]]:
        client = get_database_client()
        query = client.table("messages").select("*").eq("conversation_id", conversation_id)
        if after:
            query = query.gt("created_at", after)
        result = query.order("created_at", desc=False).execute()
        return result.data or []

    @staticmethod
    async def update_status(conversation_id: str, business_id: str, status: str) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("conversations")
            .update({"status": status, "updated_at": "now()"})
            .eq("id", conversation_id)
            .eq("business_id", business_id)
            .execute()
        )
        return result.data[0] if result.data else {}


__all__ = ["ConversationRepository"]

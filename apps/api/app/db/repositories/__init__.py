from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class CustomerRepository:
    """Supabase-backed repository for CRM customer records."""

    @staticmethod
    async def create(business_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = client.table("customers").insert({"business_id": business_id, **data}).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(business_id: str, customer_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("customers")
            .select("*")
            .eq("business_id", business_id)
            .eq("id", customer_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_for_business(business_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("customers")
            .select("*")
            .eq("business_id", business_id)
            .order("last_seen_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def upsert_identity(business_id: str, identity: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("customer_identities")
            .upsert({"business_id": business_id, **identity}, on_conflict="business_id,channel,external_id")
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def add_interaction(business_id: str, interaction: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = client.table("customer_interactions").insert({"business_id": business_id, **interaction}).execute()
        return result.data[0] if result.data else {}


__all__ = ["CustomerRepository"]

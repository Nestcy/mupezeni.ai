from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.client import get_database_client, get_service_role_client


class StoreRepository:
    @staticmethod
    async def create(business_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("stores")
            .insert({"business_id": business_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(store_id: str, business_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("stores")
            .select("*")
            .eq("id", store_id)
            .eq("business_id", business_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_by_business(business_id: str) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("stores")
            .select("*")
            .eq("business_id", business_id)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def update(store_id: str, business_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("stores")
            .update(data)
            .eq("id", store_id)
            .eq("business_id", business_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_slug_published(slug: str) -> dict[str, Any] | None:
        """Get a published store by slug (for public API)"""
        client = get_database_client()
        result = (
            client.table("stores")
            .select("*")
            .eq("slug", slug)
            .eq("status", "published")
            .single()
            .execute()
        )
        return result.data if result.data else None


class DomainRepository:
    @staticmethod
    async def create(store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("domains")
            .insert({"store_id": store_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(domain_id: str, store_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("domains")
            .select("*")
            .eq("id", domain_id)
            .eq("store_id", store_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def resolve_by_hostname(hostname: str) -> dict[str, Any] | None:
        """Resolve a hostname to an active domain"""
        client = get_database_client()
        # Normalize hostname (strip www if present, lowercase)
        normalized = hostname.lower().replace("www.", "")
        result = (
            client.table("domains")
            .select("*")
            .eq("domain", normalized)
            .eq("status", "active")
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_by_store(store_id: str) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("domains")
            .select("*")
            .eq("store_id", store_id)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def update(domain_id: str, store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("domains")
            .update(data)
            .eq("id", domain_id)
            .eq("store_id", store_id)
            .execute()
        )
        return result.data[0] if result.data else {}

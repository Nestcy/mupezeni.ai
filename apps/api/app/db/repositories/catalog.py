from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class CatalogRepository:
    @staticmethod
    async def create(store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("catalogs")
            .insert({"store_id": store_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(catalog_id: str, store_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("catalogs")
            .select("*")
            .eq("id", catalog_id)
            .eq("store_id", store_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_by_store(store_id: str, status: str | None = None) -> list[dict[str, Any]]:
        client = get_database_client()
        query = client.table("catalogs").select("*").eq("store_id", store_id)
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return result.data or []

    @staticmethod
    async def get_active_by_store(store_id: str) -> dict[str, Any] | None:
        """Get the active catalog for a store"""
        client = get_database_client()
        result = (
            client.table("catalogs")
            .select("*")
            .eq("store_id", store_id)
            .eq("status", "active")
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def update(catalog_id: str, store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("catalogs")
            .update(data)
            .eq("id", catalog_id)
            .eq("store_id", store_id)
            .execute()
        )
        return result.data[0] if result.data else {}

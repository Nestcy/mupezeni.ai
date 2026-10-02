from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class OrderRepository:
    @staticmethod
    async def create(store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("orders")
            .insert({"store_id": store_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(order_id: str, store_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("orders")
            .select("*")
            .eq("id", order_id)
            .eq("store_id", store_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def get_by_order_number(order_number: str, store_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("orders")
            .select("*")
            .eq("order_number", order_number)
            .eq("store_id", store_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_by_store(store_id: str, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        client = get_database_client()
        query = client.table("orders").select("*").eq("store_id", store_id)
        if status:
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data or []

    @staticmethod
    async def update_status(order_id: str, store_id: str, status: str) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("orders")
            .update({"status": status})
            .eq("id", order_id)
            .eq("store_id", store_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def update_payment_status(order_id: str, store_id: str, payment_status: str) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("orders")
            .update({"payment_status": payment_status})
            .eq("id", order_id)
            .eq("store_id", store_id)
            .execute()
        )
        return result.data[0] if result.data else {}


class OrderItemRepository:
    @staticmethod
    async def create(order_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("order_items")
            .insert({"order_id": order_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def list_by_order(order_id: str) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("order_items")
            .select("*")
            .eq("order_id", order_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

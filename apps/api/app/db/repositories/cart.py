from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class CartRepository:
    @staticmethod
    async def create(store_id: str, currency: str = "USD") -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("carts")
            .insert({"store_id": store_id, "currency": currency, "status": "active"})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(cart_id: str, store_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("carts")
            .select("*")
            .eq("id", cart_id)
            .eq("store_id", store_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def update_status(cart_id: str, status: str) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("carts")
            .update({"status": status})
            .eq("id", cart_id)
            .execute()
        )
        return result.data[0] if result.data else {}


class CartItemRepository:
    @staticmethod
    async def add_item(cart_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("cart_items")
            .insert({"cart_id": cart_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def list_by_cart(cart_id: str) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("cart_items")
            .select("*")
            .eq("cart_id", cart_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def get_by_id(item_id: str, cart_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("cart_items")
            .select("*")
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def update_quantity(item_id: str, quantity: int) -> dict[str, Any]:
        client = get_service_role_client()
        # Get current item to compute new subtotal
        # This is simplified; in production, fetch the item first
        result = (
            client.table("cart_items")
            .update({"quantity": quantity})
            .eq("id", item_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def delete_item(item_id: str, cart_id: str) -> bool:
        client = get_service_role_client()
        result = (
            client.table("cart_items")
            .delete()
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .execute()
        )
        return len(result.data) > 0 if result.data else False

    @staticmethod
    async def clear_cart(cart_id: str) -> int:
        """Delete all items in a cart"""
        client = get_service_role_client()
        result = (
            client.table("cart_items")
            .delete()
            .eq("cart_id", cart_id)
            .execute()
        )
        return len(result.data) if result.data else 0

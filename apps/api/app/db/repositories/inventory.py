from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class InventoryRepository:
    @staticmethod
    async def create(product_variant_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("inventory")
            .insert({"product_variant_id": product_variant_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_variant_id(variant_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("inventory")
            .select("*")
            .eq("product_variant_id", variant_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def update_quantity(variant_id: str, new_quantity: int) -> dict[str, Any]:
        """Update quantity atomically"""
        client = get_service_role_client()
        result = (
            client.table("inventory")
            .update({"quantity_on_hand": new_quantity})
            .eq("product_variant_id", variant_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def reserve_quantity(variant_id: str, quantity: int) -> dict[str, Any]:
        """Reserve quantity for an order (atomic)"""
        client = get_service_role_client()
        # Get current inventory
        inv = await InventoryRepository.get_by_variant_id(variant_id)
        if not inv:
            return {}
        available = inv.get("quantity_on_hand", 0) - inv.get("quantity_reserved", 0)
        if available < quantity:
            return {}
        new_reserved = inv.get("quantity_reserved", 0) + quantity
        result = (
            client.table("inventory")
            .update({"quantity_reserved": new_reserved})
            .eq("product_variant_id", variant_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def release_quantity(variant_id: str, quantity: int) -> dict[str, Any]:
        """Release reserved quantity (e.g., after order cancellation)"""
        client = get_service_role_client()
        inv = await InventoryRepository.get_by_variant_id(variant_id)
        if not inv:
            return {}
        new_reserved = max(0, inv.get("quantity_reserved", 0) - quantity)
        result = (
            client.table("inventory")
            .update({"quantity_reserved": new_reserved})
            .eq("product_variant_id", variant_id)
            .execute()
        )
        return result.data[0] if result.data else {}

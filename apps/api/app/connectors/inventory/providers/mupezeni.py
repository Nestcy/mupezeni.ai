from __future__ import annotations

from typing import Any

from app.connectors.inventory.interface import InventoryConnector
from app.db.repositories import InventoryRepository


class MupezeniInventoryProvider:
    """Native Mupezeni inventory provider"""

    async def get(self, product_variant_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get inventory for a product variant"""
        inventory = await InventoryRepository.get_by_variant_id(product_variant_id)
        if not inventory:
            return {"error": "inventory_not_found"}
        return inventory

    async def adjust(
        self,
        product_variant_id: str,
        quantity_change: int,
        reason: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Adjust inventory quantity"""
        inventory = await InventoryRepository.get_by_variant_id(product_variant_id)
        if not inventory:
            return {"error": "inventory_not_found"}

        new_quantity = max(0, inventory.get("quantity_on_hand", 0) + quantity_change)
        updated = await InventoryRepository.update_quantity(product_variant_id, new_quantity)
        return updated or {}

    async def reserve(
        self,
        product_variant_id: str,
        quantity: int,
        order_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Reserve inventory for an order"""
        inventory = await InventoryRepository.get_by_variant_id(product_variant_id)
        if not inventory:
            return {"error": "inventory_not_found"}

        available = inventory.get("quantity_on_hand", 0) - inventory.get(
            "quantity_reserved", 0
        )
        if available < quantity:
            return {"error": "insufficient_inventory", "available": available}

        updated = await InventoryRepository.reserve_quantity(product_variant_id, quantity)
        return updated or {}

    async def release(
        self,
        product_variant_id: str,
        quantity: int,
        order_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Release reserved inventory"""
        inventory = await InventoryRepository.get_by_variant_id(product_variant_id)
        if not inventory:
            return {"error": "inventory_not_found"}

        updated = await InventoryRepository.release_quantity(product_variant_id, quantity)
        return updated or {}

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """Execute an inventory action"""
        action_name = action.split(".")[1] if "." in action else action

        if action_name == "get":
            return await self.get(**kwargs)
        elif action_name == "adjust":
            return await self.adjust(**kwargs)
        elif action_name == "reserve":
            return await self.reserve(**kwargs)
        elif action_name == "release":
            return await self.release(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

from __future__ import annotations

from typing import Any

from app.connectors.catalog.interface import CatalogConnector
from app.db.repositories import ProductRepository, InventoryRepository, ProductVariantRepository


class MupezeniCatalogProvider:
    """Native Mupezeni catalog provider"""

    def __init__(self, catalog_id: str):
        self.catalog_id = catalog_id

    async def search_products(
        self,
        query: str | None = None,
        max_price: int | None = None,
        attributes: dict[str, Any] | None = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search products in the Mupezeni catalog"""
        products = await ProductRepository.search(
            self.catalog_id, query=query, status="active", limit=limit
        )

        # Filter by price if specified (minor units)
        if max_price is not None:
            products = [p for p in products if p.get("base_price", 0) <= max_price]

        # Could implement attribute filtering here
        # For now, return all matching

        return {
            "products": products,
            "total": len(products),
            "has_more": len(products) >= limit,
        }

    async def get_product(self, product_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get a specific product"""
        product = await ProductRepository.get_by_id(product_id, self.catalog_id)
        if not product:
            return {}
        return product

    async def check_availability(
        self, product_id: str | None = None, sku: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Check product availability and inventory status"""
        if not product_id and not sku:
            return {"available": False, "reason": "product_id or sku required"}

        # Get product
        if product_id:
            product = await ProductRepository.get_by_id(product_id, self.catalog_id)
        else:
            # Search by SKU (simplified)
            products = await ProductRepository.search(self.catalog_id, query=sku, limit=1)
            product = products[0] if products else None

        if not product:
            return {"available": False, "reason": "product_not_found"}

        if product.get("status") != "active":
            return {"available": False, "reason": "product_inactive"}

        # Check inventory
        variants = await ProductVariantRepository.list_by_product(product["id"])
        if not variants:
            # Product without variants
            return {"available": True, "quantity": 0, "reason": "no_variants"}

        total_available = 0
        for variant in variants:
            inventory = await InventoryRepository.get_by_variant_id(variant["id"])
            if inventory:
                available = inventory.get("quantity_on_hand", 0) - inventory.get(
                    "quantity_reserved", 0
                )
                total_available += max(0, available)

        return {
            "available": total_available > 0,
            "quantity": total_available,
            "product_id": product["id"],
            "sku": product.get("sku"),
        }

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """Execute a capability action"""
        action_name = action.split(".")[1] if "." in action else action

        if action_name == "search_products":
            return await self.search_products(**kwargs)
        elif action_name == "get_product":
            return await self.get_product(**kwargs)
        elif action_name == "check_availability":
            return await self.check_availability(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

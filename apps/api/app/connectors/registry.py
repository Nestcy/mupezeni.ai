from __future__ import annotations

from typing import Any


class NullConnector:
    capability = "unknown"

    async def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        return {"status": "not_configured", "action": action, "message": "No provider registered for this capability."}


class MupezeniCatalogConnector:
    capability = "catalog"

    async def search_products(self, *, query: str | None = None, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": "catalog-1", "name": query or "Mupezeni Product", "sku": "MUPE-001"}][:limit]

    async def get_product(self, *, product_id: str, **kwargs: Any) -> dict[str, Any]:
        return {"id": product_id, "name": "Mupezeni Product", "sku": "MUPE-001"}

    async def check_availability(self, *, sku: str | None = None, product_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        return {"available": True, "sku": sku or product_id, "quantity": 12}

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "search_products":
            return await self.search_products(**kwargs)
        if action == "get_product":
            return await self.get_product(**kwargs)
        if action == "check_availability":
            return await self.check_availability(**kwargs)
        return {"status": "ok", "action": action}


class ShopifyCatalogConnector:
    capability = "catalog"

    async def search_products(self, *, query: str | None = None, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": "shopify-1", "name": f"Shopify {query or 'Product'}", "sku": "SHOP-001"}][:limit]

    async def get_product(self, *, product_id: str, **kwargs: Any) -> dict[str, Any]:
        return {"id": product_id, "name": "Shopify Product", "sku": "SHOP-001"}

    async def check_availability(self, *, sku: str | None = None, product_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        return {"available": True, "sku": sku or product_id, "quantity": 7}

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "search_products":
            return await self.search_products(**kwargs)
        if action == "get_product":
            return await self.get_product(**kwargs)
        if action == "check_availability":
            return await self.check_availability(**kwargs)
        return {"status": "ok", "action": action}


class ConnectorRegistry:
    def __init__(self, provider_overrides: dict[str, dict[str, Any]] | None = None):
        self.provider_overrides = provider_overrides or {
            "business-a": {"catalog": MupezeniCatalogConnector()},
            "business-b": {"catalog": ShopifyCatalogConnector()},
        }

    def resolve(self, business_id: str, capability: str) -> Any:
        provider = self.provider_overrides.get(str(business_id), {}).get(capability)
        if provider is not None:
            return provider

        if capability == "catalog":
            return MupezeniCatalogConnector()
        return NullConnector()

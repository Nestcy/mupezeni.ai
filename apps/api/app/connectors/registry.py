from __future__ import annotations

from typing import Any

from app.connectors.catalog.providers.mupezeni import MupezeniCatalogProvider
from app.connectors.catalog.providers.shopify import ShopifyCatalogProvider
from app.connectors.inventory.providers.mupezeni import MupezeniInventoryProvider


class ConnectorNotConfigured(RuntimeError):
    pass


class NullConnector:
    """Stand-in when a business has no connector for a capability.

    Fails loudly on use. Silently returning an empty catalog would let an AI worker tell customers
    "we have nothing in stock" when the real problem is a missing connector.
    """

    def __init__(self, capability: str = "unknown"):
        self.capability = capability

    async def execute(self, action: str, **kwargs: Any) -> Any:
        raise ConnectorNotConfigured(f"No '{self.capability}' connector is configured (action: {action})")

    async def search_products(self, **kwargs: Any) -> Any:
        return await self.execute("search_products")

    async def get_product(self, **kwargs: Any) -> Any:
        return await self.execute("get_product")

    async def check_availability(self, **kwargs: Any) -> Any:
        return await self.execute("check_availability")


class ConnectorRegistry:
    """Registry that resolves business/capability -> connector provider"""

    def __init__(self, provider_overrides: dict[str, dict[str, Any]] | None = None):
        self.provider_overrides = provider_overrides or {}

    def register_provider(self, business_id: str, category: str, provider_instance: Any) -> None:
        if business_id not in self.provider_overrides:
            self.provider_overrides[business_id] = {}
        self.provider_overrides[business_id][category] = provider_instance

    def resolve(self, business_id: str, category: str, provider_name: str | None = None) -> Any:
        """
        Resolve a connector provider for a business and capability category.
        """
        # Check for test/override providers
        if business_id in self.provider_overrides:
            provider = self.provider_overrides[business_id].get(category)
            if provider:
                return provider

        if provider_name == "shopify":
            return ShopifyCatalogProvider()

        # Default to Mupezeni native providers (tenant-scoped to business_id)
        if category == "catalog":
            return MupezeniCatalogProvider(catalog_id=business_id)
        elif category == "inventory":
            return MupezeniInventoryProvider()
        elif category in ("cart", "order"):
            from app.connectors.cart.provider import NativeCartAndOrderProvider
            return NativeCartAndOrderProvider()
        else:
            return None

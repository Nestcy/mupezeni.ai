from __future__ import annotations

from typing import Any

from app.connectors.catalog.providers.mupezeni import MupezeniCatalogProvider
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

    def resolve(self, business_id: str, category: str) -> Any:
        """
        Resolve a connector provider for a business and capability category.

        For now, all businesses use Mupezeni native providers.
        Future: will query business_connectors table to support Shopify, etc.
        """
        # Check for test/override providers
        if business_id in self.provider_overrides:
            provider = self.provider_overrides[business_id].get(category)
            if provider:
                return provider

        # For Phase 3, default to Mupezeni native providers
        if category == "catalog":
            return MupezeniCatalogProvider(catalog_id="default")
        elif category == "inventory":
            return MupezeniInventoryProvider()
        else:
            return None

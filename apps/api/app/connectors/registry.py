from __future__ import annotations

from typing import Any

from app.connectors.catalog.providers.mupezeni import MupezeniCatalogProvider
from app.connectors.inventory.providers.mupezeni import MupezeniInventoryProvider


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

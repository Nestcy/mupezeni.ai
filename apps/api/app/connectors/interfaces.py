from __future__ import annotations

from typing import Any, Protocol


class CapabilityConnector(Protocol):
    capability: str

    async def execute(self, action: str, **kwargs: Any) -> Any:
        ...


class CatalogConnector(Protocol):
    async def search_products(self, *, query: str | None = None, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        ...

    async def get_product(self, *, product_id: str, **kwargs: Any) -> dict[str, Any]:
        ...

    async def check_availability(self, *, sku: str | None = None, product_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        ...

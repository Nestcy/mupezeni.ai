from __future__ import annotations

from typing import Any, Protocol


class CatalogConnector(Protocol):
    """Provider-agnostic catalog interface"""

    async def search_products(
        self,
        query: str | None = None,
        max_price: int | None = None,
        attributes: dict[str, Any] | None = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    async def get_product(self, product_id: str, **kwargs: Any) -> dict[str, Any]:
        ...

    async def check_availability(
        self, product_id: str | None = None, sku: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        ...

    async def execute(self, action: str, **kwargs: Any) -> Any:
        ...

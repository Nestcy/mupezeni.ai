from __future__ import annotations

from typing import Any, Protocol


class InventoryConnector(Protocol):
    """Provider-agnostic inventory interface"""

    async def get(
        self, product_variant_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        ...

    async def adjust(
        self,
        product_variant_id: str,
        quantity_change: int,
        reason: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    async def reserve(
        self,
        product_variant_id: str,
        quantity: int,
        order_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    async def release(
        self,
        product_variant_id: str,
        quantity: int,
        order_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...

    async def execute(self, action: str, **kwargs: Any) -> Any:
        ...

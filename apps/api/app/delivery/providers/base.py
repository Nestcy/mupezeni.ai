"""Delivery domain — DeliveryProvider Protocol interface (§20)."""
from __future__ import annotations

from typing import Protocol, Dict, Any, Optional


class DeliveryProvider(Protocol):
    """
    Provider-agnostic delivery interface (§20).
    The application must depend on this interface, returning normalized results.
    """

    async def create_delivery(
        self,
        order_id: str,
        pickup_address: Optional[Dict[str, Any]],
        delivery_address: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    async def get_delivery(self, provider_delivery_id: str) -> Dict[str, Any]:
        ...

    async def cancel_delivery(self, provider_delivery_id: str) -> Dict[str, Any]:
        ...

    async def get_tracking(self, provider_delivery_id: str) -> Dict[str, Any]:
        ...

    async def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        ...

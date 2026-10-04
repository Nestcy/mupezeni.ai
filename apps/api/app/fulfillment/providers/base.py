"""Fulfillment domain — provider interfaces."""
from __future__ import annotations

from typing import Protocol, Dict, Any, Optional


class FulfillmentProvider(Protocol):
    async def create_fulfillment(self, order_id: str, items: list) -> Dict[str, Any]:
        ...

    async def get_fulfillment(self, fulfillment_id: str) -> Dict[str, Any]:
        ...

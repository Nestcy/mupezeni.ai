"""Fulfillment domain — mock provider."""
from __future__ import annotations

import uuid
from typing import Dict, Any


class MockFulfillmentProvider:
    async def create_fulfillment(self, order_id: str, items: list) -> Dict[str, Any]:
        return {
            "provider_fulfillment_id": f"ful_mock_{uuid.uuid4().hex[:12]}",
            "order_id": order_id,
            "status": "processing",
        }

    async def get_fulfillment(self, fulfillment_id: str) -> Dict[str, Any]:
        return {
            "fulfillment_id": fulfillment_id,
            "status": "ready",
        }

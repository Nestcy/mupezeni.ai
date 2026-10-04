"""Delivery domain — Mock Delivery Provider (§20)."""
from __future__ import annotations

import uuid
from typing import Dict, Any, Optional
from app.delivery.models import DeliveryStatus


class MockDeliveryProvider:
    """
    Mock delivery provider supporting creation, tracking, cancellation, and simulation.
    """

    def __init__(self) -> None:
        self._deliveries: Dict[str, Dict[str, Any]] = {}

    async def create_delivery(
        self,
        order_id: str,
        pickup_address: Optional[Dict[str, Any]],
        delivery_address: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prov_id = f"del_mock_{uuid.uuid4().hex[:12]}"
        tracking_no = f"TRK-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "provider_delivery_id": prov_id,
            "tracking_number": tracking_no,
            "status": DeliveryStatus.PENDING.value,
            "pickup_address": pickup_address,
            "delivery_address": delivery_address,
            "metadata": metadata or {},
        }
        self._deliveries[prov_id] = record
        return record

    async def get_delivery(self, provider_delivery_id: str) -> Dict[str, Any]:
        return self._deliveries.get(
            provider_delivery_id,
            {"provider_delivery_id": provider_delivery_id, "status": DeliveryStatus.PENDING.value},
        )

    async def cancel_delivery(self, provider_delivery_id: str) -> Dict[str, Any]:
        if provider_delivery_id in self._deliveries:
            self._deliveries[provider_delivery_id]["status"] = DeliveryStatus.CANCELLED.value
        return {"provider_delivery_id": provider_delivery_id, "status": DeliveryStatus.CANCELLED.value}

    async def get_tracking(self, provider_delivery_id: str) -> Dict[str, Any]:
        deliv = await self.get_delivery(provider_delivery_id)
        return {
            "provider_delivery_id": provider_delivery_id,
            "status": deliv.get("status", DeliveryStatus.PENDING.value),
            "tracking_number": deliv.get("tracking_number"),
            "events": [
                {
                    "status": deliv.get("status", DeliveryStatus.PENDING.value),
                    "description": f"Status is {deliv.get('status')}",
                    "location": "Lusaka Central Hub",
                }
            ],
        }

    async def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        return True

    # ── Simulation helpers ──────────────────────────────────────────────────

    def simulate_status_change(self, provider_delivery_id: str, new_status: DeliveryStatus) -> Dict[str, Any]:
        if provider_delivery_id in self._deliveries:
            self._deliveries[provider_delivery_id]["status"] = new_status.value
        return {"provider_delivery_id": provider_delivery_id, "status": new_status.value}

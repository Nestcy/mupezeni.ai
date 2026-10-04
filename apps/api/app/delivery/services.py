"""Delivery domain — DeliveryService."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.delivery.models import Delivery, DeliveryStatus, DeliveryMode, DeliveryTrackingEvent
from app.delivery.providers.mock import MockDeliveryProvider
from app.delivery.errors import DeliveryNotFound


class DeliveryService:
    """
    Delivery domain service. Provider-agnostic delivery management.
    """

    def __init__(self) -> None:
        self._deliveries: Dict[str, Delivery] = {}
        self._order_map: Dict[str, Delivery] = {}  # order_id -> Delivery
        self._provider_map: Dict[str, Delivery] = {}  # "provider:provider_delivery_id" -> Delivery
        self.mock_provider = MockDeliveryProvider()
        self._emitted_events: List[Dict[str, Any]] = []

    async def create_delivery(
        self,
        *,
        business_id: str,
        order_id: str,
        provider: str = "mock",
        delivery_mode: DeliveryMode = DeliveryMode.EXTERNAL_PROVIDER,
        pickup_address: Optional[Dict[str, Any]] = None,
        delivery_address: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Delivery:
        if order_id in self._order_map:
            return self._order_map[order_id]

        delivery_id = f"del_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        prov_resp = await self.mock_provider.create_delivery(
            order_id=order_id,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            metadata=metadata,
        )

        delivery = Delivery(
            id=delivery_id,
            business_id=business_id,
            order_id=order_id,
            provider=provider,
            provider_delivery_id=prov_resp["provider_delivery_id"],
            delivery_mode=delivery_mode,
            status=DeliveryStatus.PENDING,
            tracking_number=prov_resp.get("tracking_number"),
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        self._deliveries[delivery_id] = delivery
        self._order_map[order_id] = delivery
        self._provider_map[f"{provider}:{delivery.provider_delivery_id}"] = delivery

        self._emit_event(business_id, "delivery.created", {"delivery_id": delivery_id, "order_id": order_id})
        return delivery

    def get_delivery(self, business_id: str, delivery_id: str) -> Optional[Delivery]:
        deliv = self._deliveries.get(delivery_id)
        if deliv and deliv.business_id == business_id:
            return deliv
        return None

    def get_by_order(self, business_id: str, order_id: str) -> Optional[Delivery]:
        deliv = self._order_map.get(order_id)
        if deliv and deliv.business_id == business_id:
            return deliv
        return None

    def get_tracking(self, business_id: str, delivery_id: str) -> Dict[str, Any]:
        deliv = self.get_delivery(business_id, delivery_id)
        if not deliv:
            raise DeliveryNotFound(delivery_id)
        return {
            "delivery_id": deliv.id,
            "order_id": deliv.order_id,
            "status": deliv.status.value,
            "tracking_number": deliv.tracking_number,
            "events": [
                {
                    "status": ev.status.value,
                    "location": ev.location,
                    "description": ev.description,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "provider_event_id": ev.provider_event_id,
                }
                for ev in deliv.tracking_events
            ],
        }

    def update_delivery_status(
        self,
        provider: str,
        provider_delivery_id: str,
        new_status: DeliveryStatus,
        tracking_event: Optional[DeliveryTrackingEvent] = None,
    ) -> Optional[Delivery]:
        key = f"{provider}:{provider_delivery_id}"
        delivery = self._provider_map.get(key)
        if not delivery:
            return None

        delivery.status = new_status
        delivery.updated_at = datetime.utcnow()

        if new_status == DeliveryStatus.DELIVERED:
            delivery.actual_delivery_at = datetime.utcnow()

        if tracking_event:
            delivery.tracking_events.append(tracking_event)
        else:
            delivery.tracking_events.append(
                DeliveryTrackingEvent(status=new_status, timestamp=datetime.utcnow())
            )

        event_name = f"delivery.{new_status.value}"
        self._emit_event(delivery.business_id, event_name, {"delivery_id": delivery.id, "order_id": delivery.order_id})
        return delivery

    def _emit_event(self, business_id: str, event_type: str, data: Dict[str, Any]) -> None:
        self._emitted_events.append({
            "business_id": business_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

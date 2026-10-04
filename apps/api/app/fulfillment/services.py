"""Fulfillment domain — FulfillmentService."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.fulfillment.models import Fulfillment, FulfillmentStatus, FulfillmentItem
from app.fulfillment.state import transition
from app.fulfillment.errors import FulfillmentNotFound


class FulfillmentService:
    """
    Fulfillment domain service representing the business preparing the order.
    """

    def __init__(self) -> None:
        self._fulfillments: Dict[str, Fulfillment] = {}
        self._order_map: Dict[str, Fulfillment] = {}  # order_id -> Fulfillment
        self._emitted_events: List[Dict[str, Any]] = []

    def create_fulfillment(
        self,
        *,
        business_id: str,
        order_id: str,
        items: List[Dict[str, Any]],
        notes: Optional[str] = None,
    ) -> Fulfillment:
        if order_id in self._order_map:
            return self._order_map[order_id]

        ful_id = f"ful_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        fulfillment_items = [
            FulfillmentItem(
                product_id=it["product_id"],
                quantity=it["quantity"],
                sku=it.get("sku"),
            )
            for it in items
        ]

        fulfillment = Fulfillment(
            id=ful_id,
            business_id=business_id,
            order_id=order_id,
            status=FulfillmentStatus.UNFULFILLED,
            items=fulfillment_items,
            notes=notes,
            created_at=now,
            updated_at=now,
        )

        self._fulfillments[ful_id] = fulfillment
        self._order_map[order_id] = fulfillment
        self._emit_event(business_id, "fulfillment.created", {"fulfillment_id": ful_id, "order_id": order_id})
        return fulfillment

    def get_fulfillment(self, business_id: str, fulfillment_id: str) -> Optional[Fulfillment]:
        ful = self._fulfillments.get(fulfillment_id)
        if ful and ful.business_id == business_id:
            return ful
        return None

    def get_by_order(self, business_id: str, order_id: str) -> Optional[Fulfillment]:
        ful = self._order_map.get(order_id)
        if ful and ful.business_id == business_id:
            return ful
        return None

    def mark_processing(self, business_id: str, fulfillment_id: str) -> Fulfillment:
        ful = self.get_fulfillment(business_id, fulfillment_id)
        if not ful:
            raise FulfillmentNotFound(fulfillment_id)
        ful.status = transition(ful.status, FulfillmentStatus.PROCESSING)
        ful.updated_at = datetime.utcnow()
        self._emit_event(business_id, "fulfillment.processing", {"fulfillment_id": ful.id})
        return ful

    def mark_ready(self, business_id: str, fulfillment_id: str) -> Fulfillment:
        ful = self.get_fulfillment(business_id, fulfillment_id)
        if not ful:
            raise FulfillmentNotFound(fulfillment_id)
        if ful.status == FulfillmentStatus.UNFULFILLED:
            ful.status = transition(ful.status, FulfillmentStatus.PROCESSING)
        ful.status = transition(ful.status, FulfillmentStatus.READY)
        ful.updated_at = datetime.utcnow()
        self._emit_event(business_id, "fulfillment.ready", {"fulfillment_id": ful.id, "order_id": ful.order_id})
        return ful

    def mark_fulfilled(self, business_id: str, fulfillment_id: str) -> Fulfillment:
        ful = self.get_fulfillment(business_id, fulfillment_id)
        if not ful:
            raise FulfillmentNotFound(fulfillment_id)
        ful.status = transition(ful.status, FulfillmentStatus.FULFILLED)
        ful.updated_at = datetime.utcnow()
        self._emit_event(business_id, "fulfillment.fulfilled", {"fulfillment_id": ful.id})
        return ful

    def _emit_event(self, business_id: str, event_type: str, data: Dict[str, Any]) -> None:
        self._emitted_events.append({
            "business_id": business_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

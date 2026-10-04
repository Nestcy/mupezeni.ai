"""Delivery domain — tracking normalization (§22)."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional
from app.delivery.models import DeliveryStatus, DeliveryTrackingEvent


def normalize_delivery_status(provider_status: str) -> DeliveryStatus:
    s = provider_status.lower().replace("-", "_").replace(" ", "_")
    if s in {"pending", "created"}:
        return DeliveryStatus.PENDING
    elif s in {"assigned", "driver_assigned", "accepted"}:
        return DeliveryStatus.ASSIGNED
    elif s in {"picked_up", "pickup_complete", "collected"}:
        return DeliveryStatus.PICKED_UP
    elif s in {"in_transit", "on_the_way", "transporting"}:
        return DeliveryStatus.IN_TRANSIT
    elif s in {"out_for_delivery", "arriving_soon", "delivering"}:
        return DeliveryStatus.OUT_FOR_DELIVERY
    elif s in {"delivered", "completed", "dropoff_complete"}:
        return DeliveryStatus.DELIVERED
    elif s in {"failed", "delivery_failed", "undeliverable"}:
        return DeliveryStatus.FAILED
    elif s in {"returned", "returned_to_sender"}:
        return DeliveryStatus.RETURNED
    elif s in {"cancelled", "canceled"}:
        return DeliveryStatus.CANCELLED
    return DeliveryStatus.IN_TRANSIT


def create_normalized_tracking_event(
    provider_event: Dict[str, Any],
) -> DeliveryTrackingEvent:
    status_str = provider_event.get("status", "in_transit")
    normalized_st = normalize_delivery_status(status_str)
    ts = provider_event.get("timestamp")
    if isinstance(ts, str):
        try:
            ts_dt = datetime.fromisoformat(ts)
        except ValueError:
            ts_dt = datetime.utcnow()
    elif isinstance(ts, datetime):
        ts_dt = ts
    else:
        ts_dt = datetime.utcnow()

    return DeliveryTrackingEvent(
        status=normalized_st,
        location=provider_event.get("location"),
        description=provider_event.get("description"),
        timestamp=ts_dt,
        provider_event_id=provider_event.get("provider_event_id"),
    )

"""Fulfillment domain — State machine (§18)."""
from __future__ import annotations

from app.fulfillment.models import FulfillmentStatus


_TRANSITIONS: dict[FulfillmentStatus, set[FulfillmentStatus]] = {
    FulfillmentStatus.UNFULFILLED: {FulfillmentStatus.PROCESSING, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.PROCESSING: {FulfillmentStatus.READY, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.READY: {FulfillmentStatus.FULFILLED, FulfillmentStatus.CANCELLED},
    FulfillmentStatus.FULFILLED: set(),
    FulfillmentStatus.CANCELLED: set(),
}


def transition(current: FulfillmentStatus, next_status: FulfillmentStatus) -> FulfillmentStatus:
    if next_status not in _TRANSITIONS.get(current, set()):
        raise ValueError(f"Cannot transition fulfillment from '{current}' to '{next_status}'")
    return next_status

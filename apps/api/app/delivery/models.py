"""Delivery domain — models (§19, §21, §22)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class DeliveryMode(str, Enum):
    BUSINESS_DELIVERY = "business_delivery"
    EXTERNAL_PROVIDER = "external_provider"
    CUSTOMER_PICKUP = "customer_pickup"


@dataclass
class DeliveryTrackingEvent:
    status: DeliveryStatus
    location: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None
    provider_event_id: Optional[str] = None


@dataclass
class Delivery:
    id: str
    business_id: str
    order_id: str
    provider: str                      # e.g. "mock", "yango", "dhl", "business_courier"
    provider_delivery_id: Optional[str] = None
    delivery_mode: DeliveryMode = DeliveryMode.EXTERNAL_PROVIDER
    status: DeliveryStatus = DeliveryStatus.PENDING
    tracking_number: Optional[str] = None
    pickup_address: Optional[Dict[str, Any]] = None
    delivery_address: Optional[Dict[str, Any]] = None
    estimated_delivery_at: Optional[datetime] = None
    actual_delivery_at: Optional[datetime] = None
    tracking_events: List[DeliveryTrackingEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

"""Fulfillment domain — models (§18)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class FulfillmentStatus(str, Enum):
    UNFULFILLED = "unfulfilled"
    PROCESSING = "processing"
    READY = "ready"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


@dataclass
class FulfillmentItem:
    product_id: str
    quantity: int
    sku: Optional[str] = None


@dataclass
class Fulfillment:
    id: str
    business_id: str
    order_id: str
    status: FulfillmentStatus = FulfillmentStatus.UNFULFILLED
    items: List[FulfillmentItem] = field(default_factory=list)
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

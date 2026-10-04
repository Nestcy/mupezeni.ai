"""Checkout domain — models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CheckoutStatus(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    PAYMENT_PENDING = "payment_pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class CheckoutSession:
    id: str
    business_id: str
    customer_id: str
    cart_id: str
    currency: str                    # ISO 4217, e.g. "ZMW"
    subtotal: int                    # integer minor units
    discount_total: int = 0
    shipping_total: int = 0
    tax_total: int = 0
    fee_total: int = 0
    grand_total: int = 0
    status: CheckoutStatus = CheckoutStatus.CREATED
    idempotency_key: Optional[str] = None
    order_id: Optional[str] = None   # set once order is created
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

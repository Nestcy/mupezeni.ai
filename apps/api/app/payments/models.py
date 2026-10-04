"""Payment domain — models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class Payment:
    id: str
    business_id: str
    order_id: str
    checkout_id: str
    customer_id: str
    provider: str                      # e.g. "mock", "stripe", "mtn_momo"
    provider_payment_id: str
    amount_minor: int                  # integer minor units
    currency: str                      # ISO 4217, e.g. "ZMW"
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method_type: str = "card"   # e.g. "card", "mobile_money"
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

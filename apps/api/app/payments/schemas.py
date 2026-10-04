"""Payment domain — Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.payments.models import PaymentStatus


class PaymentCreate(BaseModel):
    order_id: str
    checkout_id: str
    customer_id: str
    amount_minor: int
    currency: str = "ZMW"
    provider: str = "mock"
    payment_method_type: str = "card"
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PaymentOut(BaseModel):
    id: str
    business_id: str
    order_id: str
    checkout_id: str
    customer_id: str
    provider: str
    provider_payment_id: str
    amount_minor: int
    currency: str
    status: PaymentStatus
    payment_method_type: str
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WebhookPayload(BaseModel):
    provider: str
    external_event_id: str
    event_type: str
    provider_payment_id: str
    signature: Optional[str] = None
    data: Dict[str, Any] = {}

"""Checkout domain — Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.checkout.models import CheckoutStatus


class CheckoutCreate(BaseModel):
    cart_id: str
    currency: str = "ZMW"
    shipping_address_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class CheckoutOut(BaseModel):
    id: str
    business_id: str
    customer_id: str
    cart_id: str
    currency: str
    subtotal: int
    discount_total: int
    shipping_total: int
    tax_total: int
    fee_total: int
    grand_total: int
    status: CheckoutStatus
    idempotency_key: Optional[str] = None
    order_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

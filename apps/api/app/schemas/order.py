from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY = "ready"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class CheckoutRequest(BaseModel):
    cart_id: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    delivery_address: Optional[dict] = None


class OrderItemSnapshot(BaseModel):
    product_name: str
    product_sku: str
    variant_attributes: Optional[dict] = None
    unit_price: int
    quantity: int
    subtotal: int


class OrderResponse(BaseModel):
    id: str
    store_id: str
    order_number: str
    status: OrderStatus
    currency: str
    subtotal: int
    discount_total: int
    delivery_fee: int
    total: int
    items: list[OrderItemSnapshot] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

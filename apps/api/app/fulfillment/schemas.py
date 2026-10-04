"""Fulfillment domain — Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.fulfillment.models import FulfillmentStatus


class FulfillmentItemSchema(BaseModel):
    product_id: str
    quantity: int
    sku: Optional[str] = None


class FulfillmentCreate(BaseModel):
    order_id: str
    items: List[FulfillmentItemSchema] = []
    notes: Optional[str] = None


class FulfillmentOut(BaseModel):
    id: str
    business_id: str
    order_id: str
    status: FulfillmentStatus
    items: List[FulfillmentItemSchema] = []
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

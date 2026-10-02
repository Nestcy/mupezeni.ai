from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CartStatus(str, Enum):
    ACTIVE = "active"
    ABANDONED = "abandoned"
    CONVERTED = "converted"
    EXPIRED = "expired"


class CartCreate(BaseModel):
    store_id: str


class CartItemAdd(BaseModel):
    product_id: str
    product_variant_id: Optional[str] = None
    quantity: int = Field(..., gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0)


class CartItemResponse(BaseModel):
    id: str
    cart_id: str
    product_id: str
    product_variant_id: Optional[str]
    quantity: int
    unit_price: int
    subtotal: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: str
    store_id: str
    status: CartStatus
    total_items: int
    total_price: int
    currency: str
    items: list[CartItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

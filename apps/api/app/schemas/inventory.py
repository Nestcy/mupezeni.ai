from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InventoryStatus(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


class InventoryCreate(BaseModel):
    quantity: int = Field(..., ge=0)
    reserved_quantity: int = Field(default=0, ge=0)


class InventoryAdjustment(BaseModel):
    quantity_change: int = Field(..., description="Positive to add, negative to reduce")
    reason: Optional[str] = None


class InventoryReserve(BaseModel):
    quantity_to_reserve: int = Field(..., gt=0)
    order_id: Optional[str] = None


class InventoryRelease(BaseModel):
    quantity_to_release: int = Field(..., gt=0)
    order_id: Optional[str] = None


class InventoryResponse(BaseModel):
    id: str
    product_variant_id: str
    quantity: int
    reserved_quantity: int
    available_quantity: int
    availability_status: InventoryStatus
    updated_at: datetime

    model_config = {"from_attributes": True}

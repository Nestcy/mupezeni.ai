from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    sku: str = Field(..., min_length=1, max_length=100)
    base_price: int = Field(..., ge=0)  # Minor units
    currency: str = Field(default="USD", max_length=3)
    status: ProductStatus = ProductStatus.DRAFT


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    base_price: Optional[int] = None
    status: Optional[ProductStatus] = None


class ProductResponse(BaseModel):
    id: str
    catalog_id: str
    name: str
    slug: str
    description: Optional[str]
    sku: str
    base_price: int
    currency: str
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductVariantCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    price_override: Optional[int] = None
    currency: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: ProductStatus = ProductStatus.DRAFT


class ProductVariantUpdate(BaseModel):
    sku: Optional[str] = None
    price_override: Optional[int] = None
    currency: Optional[str] = None
    attributes: Optional[dict[str, Any]] = None
    status: Optional[ProductStatus] = None


class ProductVariantResponse(BaseModel):
    id: str
    product_id: str
    sku: str
    price_override: Optional[int]
    currency: Optional[str]
    attributes: dict[str, Any]
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

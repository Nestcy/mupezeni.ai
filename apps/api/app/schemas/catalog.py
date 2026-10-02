from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CatalogStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CatalogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class CatalogUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CatalogResponse(BaseModel):
    id: str
    store_id: str
    name: str
    description: Optional[str]
    status: CatalogStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

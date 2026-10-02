from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StoreStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class StoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, regex=r"^[a-z0-9-]+$")
    description: Optional[str] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class StorePublish(BaseModel):
    published: bool


class StoreResponse(BaseModel):
    id: str
    business_id: str
    name: str
    slug: str
    description: Optional[str]
    status: StoreStatus
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DomainType(str, Enum):
    MUPEZENI_SUBDOMAIN = "mupezeni_subdomain"
    CUSTOM = "custom"


class DomainStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    VERIFICATION_REQUIRED = "verification_required"
    DISABLED = "disabled"


class DomainCreate(BaseModel):
    domain: str = Field(..., min_length=1, max_length=255)
    domain_type: DomainType
    is_primary: bool = False


class DomainResponse(BaseModel):
    id: str
    store_id: str
    domain: str
    domain_type: DomainType
    status: DomainStatus
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

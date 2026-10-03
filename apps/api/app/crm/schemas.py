from __future__ import annotations

from pydantic import BaseModel, Field


class CustomerCreateRequest(BaseModel):
    business_id: str
    external_customer_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None


class CustomerUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class CustomerLookupRequest(BaseModel):
    business_id: str
    phone: str | None = None
    email: str | None = None
    external_customer_id: str | None = None


__all__ = [
    "CustomerCreateRequest",
    "CustomerUpdateRequest",
    "CustomerLookupRequest",
]

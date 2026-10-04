"""CRM domain models.

Field names mirror the Supabase tables (003_phase9_commerce_completion.sql: customers;
005_conversations_crm_marketing_memory.sql: customer_identities / customer_events / customer_interactions)
so rows map 1:1. Ids are strings so they work for both Postgres UUIDs and in-memory fixtures.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class Customer(BaseModel):
    id: str
    business_id: str
    external_customer_id: str | None = None   # id in Shopify / WooCommerce / CSV
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    status: CustomerStatus = CustomerStatus.ACTIVE
    first_seen_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomerIdentity(BaseModel):
    """A customer's handle on one channel (WhatsApp number, IG scoped id, web session id, ...).

    The DB column is `identity_value`; `external_id` is the name the Python code/tests use. Both read the same value.
    """
    id: str
    customer_id: str
    business_id: str | None = None             # required in the DB; optional here for lightweight in-memory use
    channel: str
    external_id: str
    display_name: str | None = None
    verified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def identity_value(self) -> str:
        return self.external_id


class CustomerInteraction(BaseModel):
    id: str
    customer_id: str
    business_id: str | None = None
    conversation_id: str | None = None
    interaction_type: str = "message"          # message, order_placed, cart_abandoned, handoff, ...
    channel: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=_utcnow)


class CustomerEvent(BaseModel):
    id: str | None = None
    business_id: str
    customer_id: str
    event_type: str
    source: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=_utcnow)


class CustomerProfile(BaseModel):
    """Minimal, worker-safe view of a customer (no internal ids beyond customer_id)."""
    customer_id: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_channel: str = "web"


__all__ = [
    "Customer", "CustomerEvent", "CustomerIdentity", "CustomerInteraction", "CustomerProfile", "CustomerStatus",
]

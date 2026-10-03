from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    """Normalized business time range."""

    start: datetime
    end: datetime
    timezone: str = "UTC"

    model_config = {"arbitrary_types_allowed": True}


class MetricDefinition(BaseModel):
    """Definition of an analytics metric."""

    name: str
    description: str
    source: str
    filters: list[str] = Field(default_factory=list)
    time_semantics: str = "period"
    currency: str | None = None
    unit: str | None = None
    value_type: str = "number"


class BusinessInsight(BaseModel):
    """Grounded operational insight."""

    type: str
    severity: str
    title: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class BusinessEvent(BaseModel):
    """Immutable business-scoped event for analytics and auditing."""

    id: str
    business_id: str
    event_type: str
    source: str
    entity_type: str
    entity_id: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BusinessOverview(BaseModel):
    period: dict[str, str]
    sales: dict[str, Any] = Field(default_factory=dict)
    orders: dict[str, Any] = Field(default_factory=dict)
    inventory: dict[str, Any] = Field(default_factory=dict)
    customers: dict[str, Any] = Field(default_factory=dict)
    carts: dict[str, Any] = Field(default_factory=dict)
    marketing: dict[str, Any] = Field(default_factory=dict)
    alerts: list[BusinessInsight] = Field(default_factory=list)


class BusinessEventStore:
    """In-memory event store for business events."""

    def __init__(self):
        self._events: dict[str, BusinessEvent] = {}

    def record(self, event: BusinessEvent) -> BusinessEvent:
        self._events[event.id] = event
        return event

    def list_by_business(self, business_id: str) -> list[BusinessEvent]:
        return [event for event in self._events.values() if event.business_id == business_id]

    def get(self, event_id: str) -> BusinessEvent | None:
        return self._events.get(event_id)


DEFAULT_TIMEZONE = "UTC"


def normalize_time_range(preset: str, *, timezone_str: str = DEFAULT_TIMEZONE, now: datetime | None = None) -> TimeRange:
    """Normalize common time presets into a deterministic time range."""

    now = now or datetime.now(timezone.utc)

    if preset == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif preset == "yesterday":
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif preset == "last_7_days":
        end = now
        start = end - timedelta(days=7)
    elif preset == "last_30_days":
        end = now
        start = end - timedelta(days=30)
    elif preset == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=32)).replace(day=1)
    elif preset == "last_month":
        first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = (first - timedelta(days=1)).replace(day=1)
        end = first
    elif preset == "custom":
        start = now - timedelta(days=7)
        end = now
    else:
        start = now - timedelta(days=7)
        end = now

    return TimeRange(start=start, end=end, timezone=timezone_str)


__all__ = [
    "BusinessEvent",
    "BusinessEventStore",
    "BusinessInsight",
    "BusinessOverview",
    "MetricDefinition",
    "TimeRange",
    "normalize_time_range",
]

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CustomerEventRecord(BaseModel):
    id: str
    business_id: str
    customer_id: str
    event_type: str
    source: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class CustomerEventService:
    """Basic event emitter for CRM changes and customer activity."""

    def __init__(self):
        self._events: list[CustomerEventRecord] = []

    def emit(self, event: CustomerEventRecord) -> CustomerEventRecord:
        self._events.append(event)
        return event

    def list_for_customer(self, customer_id: str) -> list[CustomerEventRecord]:
        return [event for event in self._events if event.customer_id == customer_id]


__all__ = ["CustomerEventRecord", "CustomerEventService"]

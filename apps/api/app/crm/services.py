from __future__ import annotations

from datetime import datetime
from typing import Any

from app.crm.models import Customer, CustomerEvent, CustomerIdentity, CustomerInteraction, CustomerProfile


class CustomerContextService:
    """Build customer context for worker execution without exposing full CRM data."""

    def __init__(self):
        self._customers: dict[str, Customer] = {}
        self._identities: dict[str, CustomerIdentity] = {}
        self._interactions: dict[str, CustomerInteraction] = {}

    def create_customer(self, customer: Customer) -> Customer:
        self._customers[customer.id] = customer
        return customer

    def create_identity(self, identity: CustomerIdentity) -> CustomerIdentity:
        self._identities[identity.id] = identity
        return identity

    def record_interaction(self, interaction: CustomerInteraction) -> CustomerInteraction:
        self._interactions[interaction.id] = interaction
        return interaction

    def get_customer(self, customer_id: str) -> Customer | None:
        return self._customers.get(customer_id)

    def get_profile(self, customer_id: str) -> CustomerProfile | None:
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        return CustomerProfile(
            customer_id=customer.id,
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone=customer.phone,
            email=customer.email,
            preferred_channel="web",
        )

    def build_context(self, customer_id: str, recent_messages: list[str] | None = None) -> dict[str, Any]:
        customer = self._customers.get(customer_id)
        if not customer:
            return {}
        return {
            "customer_id": customer.id,
            "display_name": customer.display_name or customer.first_name or "Customer",
            "recent_messages": recent_messages or [],
            "preferences": customer.metadata.get("preferences", {}),
            "status": customer.status.value,
            "channel": customer.metadata.get("preferred_channel", "web"),
        }


class IdentityResolutionService:
    """Prepare future strong-evidence identity resolution."""

    def resolve(self, *, phone: str | None = None, email: str | None = None, external_id: str | None = None) -> str | None:
        if phone:
            return f"identity:{phone}"
        if email:
            return f"identity:{email}"
        if external_id:
            return f"identity:{external_id}"
        return None


class CustomerEventBus:
    """Simple event bus for CRM events."""

    def __init__(self):
        self._events: list[CustomerEvent] = []

    def emit(self, event: CustomerEvent) -> CustomerEvent:
        self._events.append(event)
        return event

    def list_events(self, business_id: str | None = None, customer_id: str | None = None) -> list[CustomerEvent]:
        events = self._events
        if business_id is not None:
            events = [e for e in events if e.business_id == business_id]
        if customer_id is not None:
            events = [e for e in events if e.customer_id == customer_id]
        return events


__all__ = [
    "CustomerContextService",
    "IdentityResolutionService",
    "CustomerEventBus",
]

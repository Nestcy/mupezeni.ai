from __future__ import annotations

from app.crm.models import Customer, CustomerInteraction


class CustomerInteractionTracker:
    """Record normalized customer-facing interactions."""

    def __init__(self):
        self._interactions: list[CustomerInteraction] = []

    def add(self, interaction: CustomerInteraction) -> CustomerInteraction:
        self._interactions.append(interaction)
        return interaction

    def for_customer(self, customer_id: str) -> list[CustomerInteraction]:
        return [interaction for interaction in self._interactions if interaction.customer_id == customer_id]


__all__ = ["CustomerInteractionTracker"]

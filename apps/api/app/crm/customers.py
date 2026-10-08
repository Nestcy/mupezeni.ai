from __future__ import annotations

from app.crm.models import Customer, CustomerInteraction


from app.db.repositories.customers import (
    CustomerRepository,
    InMemoryCustomerRepository,
)


class CustomerManagementService:
    """Simple customer management service for CRM use cases."""

    def __init__(self, repo: CustomerRepository | None = None) -> None:
        self.repo = repo or InMemoryCustomerRepository()
        self._customers: dict[str, Customer] = {}

    def create(self, customer: Customer) -> Customer:
        self._customers[customer.id] = customer
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    self.repo.create(
                        business_id=customer.business_id,
                        display_name=customer.display_name,
                        phone=customer.phone,
                        email=customer.email,
                    )
                )
        except Exception:
            pass
        return customer

    def get(self, customer_id: str, business_id: str | None = None) -> Customer | None:
        customer = self._customers.get(customer_id)
        if customer and business_id and customer.business_id != business_id:
            return None
        return customer

    def list_for_business(self, business_id: str) -> list[Customer]:
        return [customer for customer in self._customers.values() if customer.business_id == business_id]


class CustomerInteractionService:
    """Lightweight interaction history support."""

    def __init__(self):
        self._interactions: dict[str, CustomerInteraction] = {}

    def record(self, interaction: CustomerInteraction) -> CustomerInteraction:
        self._interactions[interaction.id] = interaction
        return interaction

    def list_for_customer(self, customer_id: str) -> list[CustomerInteraction]:
        return [interaction for interaction in self._interactions.values() if interaction.customer_id == customer_id]


__all__ = ["CustomerManagementService", "CustomerInteractionService"]

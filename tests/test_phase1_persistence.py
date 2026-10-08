from __future__ import annotations

from app.crm.models import Customer, CustomerInteraction
from app.db.repositories.customer import CustomerRepository


class InMemoryCustomerRepository:
    """Fallback repo used in tests and local development."""

    def __init__(self):
        self._customers: dict[str, Customer] = {}
        self._interactions: dict[str, CustomerInteraction] = {}

    async def create(self, business_id: str, data: dict[str, object]) -> Customer:
        customer = Customer(**{"business_id": business_id, **data})
        self._customers[customer.id] = customer
        return customer

    async def get_by_id(self, business_id: str, customer_id: str) -> Customer | None:
        customer = self._customers.get(customer_id)
        if customer and customer.business_id == business_id:
            return customer
        return None

    async def list_for_business(self, business_id: str, *, limit: int = 100) -> list[Customer]:
        return [c for c in self._customers.values() if c.business_id == business_id][:limit]

    async def add_interaction(self, business_id: str, interaction: dict[str, object]) -> CustomerInteraction:
        item = CustomerInteraction(**{"business_id": business_id, **interaction})
        self._interactions[item.id] = item
        return item


class CustomerManagementService:
    """Simple customer management service for CRM use cases."""

    def __init__(self, repository: object | None = None):
        self._repository = repository or InMemoryCustomerRepository()

    async def create(self, customer: Customer) -> Customer:
        if hasattr(self._repository, "create"):
            repo_customer = await self._repository.create(customer.business_id, customer.model_dump())
            if isinstance(repo_customer, Customer):
                return repo_customer
            return Customer(**repo_customer)
        self._repository._customers[customer.id] = customer
        return customer

    async def get(self, customer_id: str, business_id: str | None = None) -> Customer | None:
        if hasattr(self._repository, "get_by_id"):
            item = await self._repository.get_by_id(business_id or "", customer_id)
            if item is None:
                return None
            return Customer(**item) if isinstance(item, dict) else item
        customer = self._repository._customers.get(customer_id)
        if customer and business_id and customer.business_id != business_id:
            return None
        return customer

    async def list_for_business(self, business_id: str) -> list[Customer]:
        if hasattr(self._repository, "list_for_business"):
            items = await self._repository.list_for_business(business_id)
            return [Customer(**item) for item in items]
        return [customer for customer in self._repository._customers.values() if customer.business_id == business_id]


class CustomerInteractionService:
    """Lightweight interaction history support."""

    def __init__(self, repository: object | None = None):
        self._repository = repository or InMemoryCustomerRepository()

    async def record(self, interaction: CustomerInteraction) -> CustomerInteraction:
        if hasattr(self._repository, "add_interaction"):
            item = await self._repository.add_interaction(interaction.business_id or "", interaction.model_dump())
            return CustomerInteraction(**item) if isinstance(item, dict) else item
        self._repository._interactions[interaction.id] = interaction
        return interaction

    async def list_for_customer(self, customer_id: str) -> list[CustomerInteraction]:
        if hasattr(self._repository, "list_for_customer"):
            items = await self._repository.list_for_customer(customer_id)
            return [CustomerInteraction(**item) for item in items]
        return [interaction for interaction in self._repository._interactions.values() if interaction.customer_id == customer_id]


__all__ = ["CustomerManagementService", "CustomerInteractionService", "InMemoryCustomerRepository"]

from __future__ import annotations

from app.workers.business_management.definition import create_business_management_worker
from app.workers.customer_revenue.definition import create_customer_revenue_worker
from app.workers.marketing.definition import create_marketing_worker


class WorkerLoader:
    """Load production workers into the registry."""

    @staticmethod
    def load_production_workers(registry) -> None:
        registry.register(create_customer_revenue_worker())
        registry.register(create_marketing_worker())
        registry.register(create_business_management_worker())


__all__ = ["WorkerLoader"]

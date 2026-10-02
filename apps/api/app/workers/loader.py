from __future__ import annotations

from app.workers.customer_revenue.definition import create_customer_revenue_worker


class WorkerLoader:
    """
    Load worker definitions into the Worker Registry.
    """

    @staticmethod
    def load_production_workers(registry) -> None:
        """
        Load all production workers into the registry.
        """
        # Customer Revenue Worker
        registry.register(create_customer_revenue_worker())

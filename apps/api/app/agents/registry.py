from __future__ import annotations

from typing import Optional

from app.agents.contracts import WorkerDefinition, AutonomyLevel


class WorkerRegistry:
    """Registry of available workers"""

    def __init__(self):
        self._workers: dict[str, WorkerDefinition] = {}
        self._init_default_workers()

    def _init_default_workers(self) -> None:
        """Initialize built-in workers"""
        # Test worker for infrastructure validation
        self.register(
            WorkerDefinition(
                id="echo_worker",
                name="Echo Worker",
                purpose="Test worker for infrastructure validation",
                version="1.0",
                instructions="You are a test assistant. You can search products and check inventory. Respond to user queries using the available tools.",
                capabilities=[
                    "catalog.search_products",
                    "catalog.get_product",
                    "catalog.check_availability",
                    "inventory.get",
                ],
                autonomy_level=AutonomyLevel.BOUNDED,
                max_iterations=5,
                max_tool_calls=10,
                max_execution_time_seconds=30,
                status="active",
            )
        )

    def register(self, worker: WorkerDefinition) -> None:
        """Register a worker definition"""
        self._workers[worker.id] = worker

    def get(self, worker_id: str) -> WorkerDefinition | None:
        """Retrieve a worker definition by ID"""
        return self._workers.get(worker_id)

    def list_all(self) -> list[WorkerDefinition]:
        """List all registered workers"""
        return list(self._workers.values())

    def list_active(self) -> list[WorkerDefinition]:
        """List only active workers"""
        return [w for w in self._workers.values() if w.status == "active"]

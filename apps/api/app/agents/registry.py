from __future__ import annotations

from app.agents.contracts import WorkerDefinition, AutonomyLevel


class WorkerRegistry:
    """Simplified registry used by the CRM/conversation infrastructure for worker lookup."""

    def __init__(self):
        self._workers: dict[str, WorkerDefinition] = {}

    def register(self, worker: WorkerDefinition) -> None:
        self._workers[worker.id] = worker

    def get(self, worker_id: str) -> WorkerDefinition | None:
        return self._workers.get(worker_id)


__all__ = ["WorkerRegistry"]

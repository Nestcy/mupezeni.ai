"""Payment domain — Idempotency management (§13)."""
from __future__ import annotations

from typing import Set, Dict, Optional
from datetime import datetime
from app.core.commerce_errors import DuplicateWebhook


class IdempotencyStore:
    """
    In-memory idempotency store for testing & single-instance runtime.
    Backed by database uniqueness constraints in production (provider + external_event_id).
    """

    def __init__(self) -> None:
        self._processed_events: Set[str] = set()       # "provider:external_event_id"
        self._idempotency_keys: Dict[str, str] = {}    # "business_id:idempotency_key" -> resource_id

    def check_and_record_event(self, provider: str, external_event_id: str) -> None:
        """
        Record a webhook event ID idempotently.
        Raises DuplicateWebhook if already processed.
        """
        key = f"{provider}:{external_event_id}"
        if key in self._processed_events:
            raise DuplicateWebhook(external_event_id)
        self._processed_events.add(key)

    def is_event_processed(self, provider: str, external_event_id: str) -> bool:
        return f"{provider}:{external_event_id}" in self._processed_events

    def get_resource_by_key(self, business_id: str, idempotency_key: str) -> Optional[str]:
        return self._idempotency_keys.get(f"{business_id}:{idempotency_key}")

    def save_key(self, business_id: str, idempotency_key: str, resource_id: str) -> None:
        self._idempotency_keys[f"{business_id}:{idempotency_key}"] = resource_id

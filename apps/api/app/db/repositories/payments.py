from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class PaymentRepositoryProtocol(Protocol):
    async def create(
        self,
        business_id: str,
        order_id: str,
        checkout_id: str,
        customer_id: str,
        amount_minor: int,
        currency: str = "ZMW",
        provider: str = "mock",
        payment_method_type: str = "card",
        idempotency_key: str | None = None,
        provider_payment_id: str | None = None,
        status: str = "pending",
    ) -> dict[str, Any]: ...

    async def get(
        self, payment_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def get_by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> dict[str, Any] | None: ...

    async def update_status(
        self, payment_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...


class SupabasePaymentRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self,
        business_id: str,
        order_id: str,
        checkout_id: str,
        customer_id: str,
        amount_minor: int,
        currency: str = "ZMW",
        provider: str = "mock",
        payment_method_type: str = "card",
        idempotency_key: str | None = None,
        provider_payment_id: str | None = None,
        status: str = "pending",
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "order_id": order_id,
            "checkout_id": checkout_id,
            "customer_id": customer_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "provider": provider,
            "payment_method_type": payment_method_type,
            "idempotency_key": idempotency_key,
            "provider_payment_id": provider_payment_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("payments").insert(data).execute()
        return res.data[0] if res.data else data

    async def get(
        self, payment_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("payments").select("*").eq("id", payment_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def get_by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> dict[str, Any] | None:
        res = (
            self._client()
            .table("payments")
            .select("*")
            .eq("provider", provider)
            .eq("provider_payment_id", provider_payment_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    async def update_status(
        self, payment_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        q = self._client().table("payments").update(updates).eq("id", payment_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self.payments: dict[str, dict[str, Any]] = {}
        self.provider_map: dict[tuple[str, str], str] = {}  # (provider, pid) -> payment_id

    async def create(
        self,
        business_id: str,
        order_id: str,
        checkout_id: str,
        customer_id: str,
        amount_minor: int,
        currency: str = "ZMW",
        provider: str = "mock",
        payment_method_type: str = "card",
        idempotency_key: str | None = None,
        provider_payment_id: str | None = None,
        status: str = "pending",
    ) -> dict[str, Any]:
        pid = str(uuid.uuid4())
        payment = {
            "id": pid,
            "business_id": business_id,
            "order_id": order_id,
            "checkout_id": checkout_id,
            "customer_id": customer_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "provider": provider,
            "payment_method_type": payment_method_type,
            "idempotency_key": idempotency_key,
            "provider_payment_id": provider_payment_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.payments[pid] = payment
        if provider and provider_payment_id:
            self.provider_map[(provider, provider_payment_id)] = pid
        return payment

    async def get(
        self, payment_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        payment = self.payments.get(payment_id)
        if not payment:
            return None
        if business_id and payment.get("business_id") != business_id:
            return None
        return dict(payment)

    async def get_by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> dict[str, Any] | None:
        pid = self.provider_map.get((provider, provider_payment_id))
        if pid:
            return await self.get(pid)
        return None

    async def update_status(
        self, payment_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        payment = self.payments.get(payment_id)
        if not payment:
            return None
        if business_id and payment.get("business_id") != business_id:
            return None
        payment["status"] = status
        payment["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(payment)

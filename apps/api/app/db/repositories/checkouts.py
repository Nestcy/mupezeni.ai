from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class CheckoutRepositoryProtocol(Protocol):
    async def create(
        self,
        business_id: str,
        customer_id: str,
        cart_id: str,
        currency: str,
        subtotal_minor: int,
        shipping_minor: int,
        tax_minor: int,
        fee_minor: int,
        grand_total_minor: int,
        line_items: list[dict[str, Any]],
        idempotency_key: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]: ...

    async def get(
        self, checkout_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def get_by_idempotency(
        self, business_id: str, idempotency_key: str
    ) -> dict[str, Any] | None: ...

    async def complete(
        self, checkout_id: str, order_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def update_status(
        self, checkout_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...


class SupabaseCheckoutRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self,
        business_id: str,
        customer_id: str,
        cart_id: str,
        currency: str,
        subtotal_minor: int,
        shipping_minor: int,
        tax_minor: int,
        fee_minor: int,
        grand_total_minor: int,
        line_items: list[dict[str, Any]],
        idempotency_key: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "customer_id": customer_id,
            "cart_id": cart_id,
            "currency": currency,
            "subtotal": subtotal_minor,
            "shipping_total": shipping_minor,
            "tax_total": tax_minor,
            "fee_total": fee_minor,
            "grand_total": grand_total_minor,
            "idempotency_key": idempotency_key,
            "status": "created",
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("checkout_sessions").insert(data).execute()
        rec = res.data[0] if res.data else data
        rec["line_items"] = line_items
        return rec

    async def get(
        self, checkout_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("checkout_sessions").select("*").eq("id", checkout_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def get_by_idempotency(
        self, business_id: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        res = (
            self._client()
            .table("checkout_sessions")
            .select("*")
            .eq("business_id", business_id)
            .eq("idempotency_key", idempotency_key)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    async def complete(
        self, checkout_id: str, order_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        updates = {
            "status": "completed",
            "order_id": order_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        q = (
            self._client()
            .table("checkout_sessions")
            .update(updates)
            .eq("id", checkout_id)
        )
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def update_status(
        self, checkout_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        q = (
            self._client()
            .table("checkout_sessions")
            .update(updates)
            .eq("id", checkout_id)
        )
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None


class InMemoryCheckoutRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.idempotency_map: dict[tuple[str, str], str] = {}  # (biz, key) -> id

    async def create(
        self,
        business_id: str,
        customer_id: str,
        cart_id: str,
        currency: str,
        subtotal_minor: int,
        shipping_minor: int,
        tax_minor: int,
        fee_minor: int,
        grand_total_minor: int,
        line_items: list[dict[str, Any]],
        idempotency_key: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        cid = str(uuid.uuid4())
        session = {
            "id": cid,
            "business_id": business_id,
            "customer_id": customer_id,
            "cart_id": cart_id,
            "currency": currency,
            "subtotal": subtotal_minor,
            "shipping_total": shipping_minor,
            "tax_total": tax_minor,
            "fee_total": fee_minor,
            "grand_total": grand_total_minor,
            "line_items": line_items,
            "idempotency_key": idempotency_key,
            "status": "created",
            "order_id": None,
            "expires_at": expires_at,
            "completed_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sessions[cid] = session
        if idempotency_key:
            self.idempotency_map[(business_id, idempotency_key)] = cid
        return session

    async def get(
        self, checkout_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        session = self.sessions.get(checkout_id)
        if not session:
            return None
        if business_id and session.get("business_id") != business_id:
            return None
        return dict(session)

    async def get_by_idempotency(
        self, business_id: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        cid = self.idempotency_map.get((business_id, idempotency_key))
        if cid:
            return await self.get(cid)
        return None

    async def complete(
        self, checkout_id: str, order_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        session = self.sessions.get(checkout_id)
        if not session:
            return None
        if business_id and session.get("business_id") != business_id:
            return None
        session["status"] = "completed"
        session["order_id"] = order_id
        session["completed_at"] = datetime.now(timezone.utc).isoformat()
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(session)

    async def update_status(
        self, checkout_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        session = self.sessions.get(checkout_id)
        if not session:
            return None
        if business_id and session.get("business_id") != business_id:
            return None
        session["status"] = status
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(session)

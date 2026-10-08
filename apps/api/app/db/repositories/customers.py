from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class CustomerRepository(Protocol):
    async def create(
        self,
        business_id: str,
        display_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]: ...

    async def get(
        self, customer_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def list_for_business(self, business_id: str) -> list[dict[str, Any]]: ...

    async def resolve_customer(
        self,
        business_id: str,
        channel: str,
        identity_value: str,
        display_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> tuple[str, bool]: ...


class SupabaseCustomerRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self,
        business_id: str,
        display_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "display_name": display_name,
            "phone": phone,
            "email": email,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("customers").insert(data).execute()
        return res.data[0] if res.data else data

    async def get(
        self, customer_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("customers").select("*").eq("id", customer_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def list_for_business(self, business_id: str) -> list[dict[str, Any]]:
        res = (
            self._client()
            .table("customers")
            .select("*")
            .eq("business_id", business_id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    async def resolve_customer(
        self,
        business_id: str,
        channel: str,
        identity_value: str,
        display_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> tuple[str, bool]:
        """Atomic customer resolution via resolve_customer() stored procedure (migration 006)."""
        res = self._client().rpc(
            "resolve_customer",
            {
                "p_business_id": business_id,
                "p_channel": channel,
                "p_identity_value": identity_value,
                "p_display_name": display_name,
                "p_phone": phone,
                "p_email": email,
            },
        ).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            return row["out_customer_id"], row["out_created"]
        # Fallback if RPC fails or table is populated manually
        created = await self.create(business_id, display_name, phone, email)
        return created["id"], True


class InMemoryCustomerRepository:
    def __init__(self) -> None:
        self.customers: dict[str, dict[str, Any]] = {}
        self.identities: dict[tuple[str, str, str], str] = {}  # (biz, ch, val) -> customer_id

    async def create(
        self,
        business_id: str,
        display_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        cid = str(uuid.uuid4())
        item = {
            "id": cid,
            "business_id": business_id,
            "display_name": display_name,
            "phone": phone,
            "email": email,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.customers[cid] = item
        return item

    async def get(
        self, customer_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        item = self.customers.get(customer_id)
        if item and business_id and item["business_id"] != business_id:
            return None
        return item

    async def list_for_business(self, business_id: str) -> list[dict[str, Any]]:
        return [c for c in self.customers.values() if c["business_id"] == business_id]

    async def resolve_customer(
        self,
        business_id: str,
        channel: str,
        identity_value: str,
        display_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> tuple[str, bool]:
        key = (business_id, channel, identity_value)
        if key in self.identities:
            cid = self.identities[key]
            if cid in self.customers:
                self.customers[cid]["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            return cid, False

        item = await self.create(business_id, display_name, phone, email)
        cid = item["id"]
        self.identities[key] = cid
        return cid, True

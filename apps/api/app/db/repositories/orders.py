from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class OrderRepositoryProtocol(Protocol):
    async def create(
        self,
        business_id: str,
        customer_id: str,
        order_number: str,
        currency: str,
        grand_total_minor: int,
        subtotal_minor: int = 0,
        shipping_minor: int = 0,
        status: str = "pending",
        items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

    async def get(
        self, order_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def list_for_business(
        self, business_id: str, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    async def update_status(
        self, order_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...


class SupabaseOrderRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self,
        business_id: str,
        customer_id: str,
        order_number: str,
        currency: str,
        grand_total_minor: int,
        subtotal_minor: int = 0,
        shipping_minor: int = 0,
        status: str = "pending",
        items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "customer_id": customer_id,
            "order_number": order_number,
            "currency": currency,
            "grand_total": grand_total_minor,
            "subtotal": subtotal_minor,
            "shipping_total": shipping_minor,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("orders").insert(data).execute()
        order = res.data[0] if res.data else data
        order_id = order.get("id")

        if items and order_id:
            order_items = [
                {
                    "order_id": order_id,
                    "product_id": i.get("product_id"),
                    "variant_id": i.get("variant_id"),
                    "quantity": i.get("quantity", 1),
                    "unit_price": i.get("unit_price_minor", 0),
                    "total_price": i.get("total_price_minor", i.get("unit_price_minor", 0) * i.get("quantity", 1)),
                }
                for i in items
            ]
            self._client().table("order_items").insert(order_items).execute()
            order["items"] = items

        return order

    async def get(
        self, order_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("orders").select("*").eq("id", order_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        if not res.data:
            return None
        order = res.data[0]
        items_res = (
            self._client()
            .table("order_items")
            .select("*")
            .eq("order_id", order_id)
            .execute()
        )
        order["items"] = items_res.data or []
        return order

    async def list_for_business(
        self, business_id: str, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        q = (
            self._client()
            .table("orders")
            .select("*")
            .eq("business_id", business_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            q = q.eq("status", status)
        res = q.execute()
        return res.data or []

    async def update_status(
        self, order_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = (
            self._client()
            .table("orders")
            .update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", order_id)
        )
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[str, dict[str, Any]] = {}
        self.items: dict[str, list[dict[str, Any]]] = {}

    async def create(
        self,
        business_id: str,
        customer_id: str,
        order_number: str,
        currency: str,
        grand_total_minor: int,
        subtotal_minor: int = 0,
        shipping_minor: int = 0,
        status: str = "pending",
        items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        oid = str(uuid.uuid4())
        order = {
            "id": oid,
            "business_id": business_id,
            "customer_id": customer_id,
            "order_number": order_number,
            "currency": currency,
            "grand_total": grand_total_minor,
            "subtotal": subtotal_minor,
            "shipping_total": shipping_minor,
            "status": status,
            "items": items or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.orders[oid] = order
        self.items[oid] = list(items or [])
        return order

    async def get(
        self, order_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        order = self.orders.get(order_id)
        if not order:
            return None
        if business_id and order.get("business_id") != business_id:
            return None
        order_copy = dict(order)
        order_copy["items"] = list(self.items.get(order_id, []))
        return order_copy

    async def list_for_business(
        self, business_id: str, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        results = [
            o for o in self.orders.values() if o.get("business_id") == business_id
        ]
        if status:
            results = [o for o in results if o.get("status") == status]
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    async def update_status(
        self, order_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        order = self.orders.get(order_id)
        if not order:
            return None
        if business_id and order.get("business_id") != business_id:
            return None
        order["status"] = status
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        return order

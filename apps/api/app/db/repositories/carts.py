from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class CartRepositoryProtocol(Protocol):
    async def create(
        self, business_id: str, customer_id: str, currency: str = "ZMW"
    ) -> dict[str, Any]: ...

    async def get(
        self, cart_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def get_active(
        self, business_id: str, customer_id: str
    ) -> dict[str, Any] | None: ...

    async def add_item(
        self,
        cart_id: str,
        product_id: str,
        quantity: int,
        variant_id: str | None = None,
        unit_price_minor: int = 0,
    ) -> dict[str, Any]: ...

    async def update_item(
        self, cart_id: str, item_id: str, quantity: int
    ) -> dict[str, Any] | None: ...

    async def remove_item(self, cart_id: str, item_id: str) -> bool: ...

    async def deactivate(self, cart_id: str) -> bool: ...


class SupabaseCartRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create(
        self, business_id: str, customer_id: str, currency: str = "ZMW"
    ) -> dict[str, Any]:
        data = {
            "customer_id": customer_id,
            "currency": currency,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("carts").insert(data).execute()
        cart = res.data[0] if res.data else data
        cart["business_id"] = business_id
        cart["items"] = []
        return cart

    async def get(
        self, cart_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("carts").select("*").eq("id", cart_id)
        res = q.execute()
        if not res.data:
            return None
        cart = res.data[0]
        # Fetch items
        items_res = (
            self._client()
            .table("cart_items")
            .select("*")
            .eq("cart_id", cart_id)
            .order("created_at")
            .execute()
        )
        cart["items"] = items_res.data or []
        if business_id:
            cart["business_id"] = business_id
        return cart

    async def get_active(
        self, business_id: str, customer_id: str
    ) -> dict[str, Any] | None:
        res = (
            self._client()
            .table("carts")
            .select("*")
            .eq("customer_id", customer_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return await self.get(res.data[0]["id"], business_id=business_id)

    async def add_item(
        self,
        cart_id: str,
        product_id: str,
        quantity: int,
        variant_id: str | None = None,
        unit_price_minor: int = 0,
    ) -> dict[str, Any]:
        data = {
            "cart_id": cart_id,
            "product_id": product_id,
            "quantity": quantity,
            "variant_id": variant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("cart_items").insert(data).execute()
        return res.data[0] if res.data else data

    async def update_item(
        self, cart_id: str, item_id: str, quantity: int
    ) -> dict[str, Any] | None:
        res = (
            self._client()
            .table("cart_items")
            .update({"quantity": quantity})
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .execute()
        )
        return res.data[0] if res.data else None

    async def remove_item(self, cart_id: str, item_id: str) -> bool:
        res = (
            self._client()
            .table("cart_items")
            .delete()
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .execute()
        )
        return bool(res.data)

    async def deactivate(self, cart_id: str) -> bool:
        res = (
            self._client()
            .table("carts")
            .update({"status": "inactive"})
            .eq("id", cart_id)
            .execute()
        )
        return bool(res.data)


class InMemoryCartRepository:
    def __init__(self) -> None:
        self.carts: dict[str, dict[str, Any]] = {}
        self.items: dict[str, list[dict[str, Any]]] = {}

    async def create(
        self, business_id: str, customer_id: str, currency: str = "ZMW"
    ) -> dict[str, Any]:
        cid = str(uuid.uuid4())
        cart = {
            "id": cid,
            "business_id": business_id,
            "customer_id": customer_id,
            "currency": currency,
            "status": "active",
            "is_active": True,
            "items": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.carts[cid] = cart
        self.items[cid] = []
        return cart

    async def get(
        self, cart_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        cart = self.carts.get(cart_id)
        if not cart:
            return None
        if business_id and cart.get("business_id") != business_id:
            return None
        cart_copy = dict(cart)
        cart_copy["items"] = list(self.items.get(cart_id, []))
        return cart_copy

    async def get_active(
        self, business_id: str, customer_id: str
    ) -> dict[str, Any] | None:
        for c in self.carts.values():
            if (
                c.get("business_id") == business_id
                and c.get("customer_id") == customer_id
                and c.get("status") == "active"
            ):
                return await self.get(c["id"])
        return None

    async def add_item(
        self,
        cart_id: str,
        product_id: str,
        quantity: int,
        variant_id: str | None = None,
        unit_price_minor: int = 0,
    ) -> dict[str, Any]:
        item = {
            "id": str(uuid.uuid4()),
            "cart_id": cart_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "unit_price_minor": unit_price_minor,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.items.setdefault(cart_id, []).append(item)
        if cart_id in self.carts:
            self.carts[cart_id]["items"] = list(self.items[cart_id])
        return item

    async def update_item(
        self, cart_id: str, item_id: str, quantity: int
    ) -> dict[str, Any] | None:
        for item in self.items.get(cart_id, []):
            if item["id"] == item_id:
                item["quantity"] = quantity
                return item
        return None

    async def remove_item(self, cart_id: str, item_id: str) -> bool:
        before = len(self.items.get(cart_id, []))
        self.items[cart_id] = [i for i in self.items.get(cart_id, []) if i["id"] != item_id]
        if cart_id in self.carts:
            self.carts[cart_id]["items"] = list(self.items[cart_id])
        return len(self.items.get(cart_id, [])) < before

    async def deactivate(self, cart_id: str) -> bool:
        if cart_id in self.carts:
            self.carts[cart_id]["status"] = "inactive"
            self.carts[cart_id]["is_active"] = False
            return True
        return False

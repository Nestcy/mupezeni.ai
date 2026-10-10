from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.repositories.cart import CartItemRepository, CartRepository
from app.db.repositories.order import OrderItemRepository, OrderRepository


class InMemoryCartRepository:
    """Fallback repository used in tests and local development when Supabase is not configured."""

    def __init__(self):
        self._carts: dict[str, dict[str, Any]] = {}
        self._items: dict[str, list[dict[str, Any]]] = {}

    async def create(self, store_id: str, currency: str = "ZMW") -> dict[str, Any]:
        cart_id = f"cart_{len(self._carts) + 1:06d}"
        record = {
            "id": cart_id,
            "store_id": store_id,
            "currency": currency,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._carts[cart_id] = record
        self._items[cart_id] = []
        return record

    async def get_by_id(self, cart_id: str, store_id: str) -> dict[str, Any] | None:
        item = self._carts.get(cart_id)
        if item and item.get("store_id") == store_id:
            return item
        return None

    async def update_status(self, cart_id: str, status: str) -> dict[str, Any]:
        cart = self._carts.get(cart_id)
        if cart is None:
            return {}
        cart["status"] = status
        cart["updated_at"] = datetime.utcnow().isoformat()
        return cart


class InMemoryCartItemRepository:
    def __init__(self):
        self._items: dict[str, list[dict[str, Any]]] = {}

    async def add_item(self, cart_id: str, data: dict[str, Any]) -> dict[str, Any]:
        item = {**data, "id": data.get("id") or f"item_{len(self._items.get(cart_id, [])) + 1:06d}", "cart_id": cart_id}
        item.setdefault("created_at", datetime.utcnow().isoformat())
        self._items.setdefault(cart_id, []).append(item)
        return item

    async def list_by_cart(self, cart_id: str) -> list[dict[str, Any]]:
        return list(self._items.get(cart_id, []))

    async def get_by_id(self, item_id: str, cart_id: str) -> dict[str, Any] | None:
        for item in self._items.get(cart_id, []):
            if item.get("id") == item_id:
                return item
        return None

    async def update_quantity(self, item_id: str, quantity: int) -> dict[str, Any]:
        for cart_id, items in self._items.items():
            for item in items:
                if item.get("id") == item_id:
                    item["quantity"] = quantity
                    return item
        return {}

    async def delete_item(self, item_id: str, cart_id: str) -> bool:
        items = self._items.get(cart_id, [])
        filtered = [item for item in items if item.get("id") != item_id]
        if len(filtered) != len(items):
            self._items[cart_id] = filtered
            return True
        return False

    async def clear_cart(self, cart_id: str) -> int:
        total = len(self._items.get(cart_id, []))
        self._items[cart_id] = []
        return total


class CartService:
    """Cart lifecycle service with repository injection. Default path is in-memory for tests."""

    def __init__(self, cart_repo: Any | None = None, item_repo: Any | None = None):
        self._cart_repo = cart_repo or InMemoryCartRepository()
        self._item_repo = item_repo or InMemoryCartItemRepository()

    async def create_cart(self, store_id: str, *, currency: str = "ZMW") -> dict[str, Any]:
        if hasattr(self._cart_repo, "create"):
            return await self._cart_repo.create(store_id, currency)
        return await self._cart_repo.create(store_id, currency=currency)

    async def get_cart(self, cart_id: str, store_id: str) -> dict[str, Any] | None:
        if hasattr(self._cart_repo, "get_by_id"):
            return await self._cart_repo.get_by_id(cart_id, store_id)
        return None

    async def add_item(self, cart_id: str, item: dict[str, Any]) -> dict[str, Any]:
        if hasattr(self._item_repo, "add_item"):
            return await self._item_repo.add_item(cart_id, item)
        return item

    async def list_items(self, cart_id: str) -> list[dict[str, Any]]:
        if hasattr(self._item_repo, "list_by_cart"):
            return await self._item_repo.list_by_cart(cart_id)
        return []

    async def update_quantity(self, item_id: str, quantity: int) -> dict[str, Any]:
        if hasattr(self._item_repo, "update_quantity"):
            return await self._item_repo.update_quantity(item_id, quantity)
        return {}

    async def remove_item(self, item_id: str, cart_id: str) -> bool:
        if hasattr(self._item_repo, "delete_item"):
            return await self._item_repo.delete_item(item_id, cart_id)
        return False

    async def clear_cart(self, cart_id: str) -> int:
        if hasattr(self._item_repo, "clear_cart"):
            return await self._item_repo.clear_cart(cart_id)
        return 0


class InMemoryOrderRepository:
    def __init__(self):
        self._orders: dict[str, dict[str, Any]] = {}
        self._items: dict[str, list[dict[str, Any]]] = {}

    async def create(self, store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        order_id = str(data.get("id") or f"ord_{len(self._orders) + 1:06d}")
        record = {**data, "id": order_id, "store_id": store_id}
        record.setdefault("created_at", datetime.utcnow().isoformat())
        record.setdefault("updated_at", datetime.utcnow().isoformat())
        self._orders[order_id] = record
        return record

    async def get_by_id(self, order_id: str, store_id: str) -> dict[str, Any] | None:
        item = self._orders.get(order_id)
        if item and item.get("store_id") == store_id:
            return item
        return None

    async def list_by_store(self, store_id: str, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        items = [item for item in self._orders.values() if item.get("store_id") == store_id]
        if status:
            items = [item for item in items if item.get("status") == status]
        return items[:limit]

    async def update_status(self, order_id: str, store_id: str, status: str) -> dict[str, Any]:
        item = self._orders.get(order_id)
        if item and item.get("store_id") == store_id:
            item["status"] = status
            item["updated_at"] = datetime.utcnow().isoformat()
            return item
        return {}


class InMemoryOrderItemRepository:
    def __init__(self):
        self._items: dict[str, list[dict[str, Any]]] = {}

    async def create(self, order_id: str, data: dict[str, Any]) -> dict[str, Any]:
        item = {**data, "id": data.get("id") or f"line_{len(self._items.get(order_id, [])) + 1:06d}", "order_id": order_id}
        item.setdefault("created_at", datetime.utcnow().isoformat())
        self._items.setdefault(order_id, []).append(item)
        return item

    async def list_by_order(self, order_id: str) -> list[dict[str, Any]]:
        return list(self._items.get(order_id, []))


class OrderService:
    """Order management service with repository injection. Default path uses in-memory storage."""

    def __init__(self, order_repo: Any | None = None, item_repo: Any | None = None):
        self._order_repo = order_repo or InMemoryOrderRepository()
        self._item_repo = item_repo or InMemoryOrderItemRepository()

    async def create_order(self, store_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self._order_repo.create(store_id, data)

    async def get_order(self, order_id: str, store_id: str) -> dict[str, Any] | None:
        return await self._order_repo.get_by_id(order_id, store_id)

    async def list_orders(self, store_id: str, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if hasattr(self._order_repo, "list_by_store"):
            return await self._order_repo.list_by_store(store_id, status=status, limit=limit)
        return []

    async def add_item(self, order_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self._item_repo.create(order_id, data)

    async def list_order_items(self, order_id: str) -> list[dict[str, Any]]:
        if hasattr(self._item_repo, "list_by_order"):
            return await self._item_repo.list_by_order(order_id)
        return []


__all__ = [
    "CartService",
    "OrderService",
    "InMemoryCartRepository",
    "InMemoryCartItemRepository",
    "InMemoryOrderRepository",
    "InMemoryOrderItemRepository",
]

from __future__ import annotations

import uuid
from typing import Any

from app.db.repositories.carts import (
    CartRepositoryProtocol,
    InMemoryCartRepository,
    SupabaseCartRepository,
)
from app.db.repositories.orders import (
    InMemoryOrderRepository,
    OrderRepositoryProtocol,
    SupabaseOrderRepository,
)


class NativeCartAndOrderProvider:
    """Connector provider executing cart.* and order.* capabilities against persistent repositories."""

    def __init__(
        self,
        cart_repo: CartRepositoryProtocol | None = None,
        order_repo: OrderRepositoryProtocol | None = None,
    ) -> None:
        self.cart_repo = cart_repo or SupabaseCartRepository()
        self.order_repo = order_repo or SupabaseOrderRepository()

    # ── Cart capabilities ──────────────────────────────────────────────────────

    async def create_cart(
        self,
        business_id: str,
        customer_id: str,
        currency: str = "ZMW",
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.cart_repo.create(business_id, customer_id, currency=currency)

    async def get_cart(
        self,
        cart_id: str,
        business_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        cart = await self.cart_repo.get(cart_id, business_id=business_id)
        return cart or {}

    async def add_item_to_cart(
        self,
        cart_id: str,
        product_id: str,
        quantity: int = 1,
        variant_id: str | None = None,
        unit_price_minor: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.cart_repo.add_item(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
            variant_id=variant_id,
            unit_price_minor=unit_price_minor,
        )

    async def update_cart_item(
        self,
        cart_id: str,
        item_id: str,
        quantity: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        res = await self.cart_repo.update_item(cart_id, item_id, quantity)
        return res or {}

    async def remove_cart_item(
        self,
        cart_id: str,
        item_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        removed = await self.cart_repo.remove_item(cart_id, item_id)
        return {"success": removed, "item_id": item_id}

    # ── Order capabilities ─────────────────────────────────────────────────────

    async def create_order(
        self,
        business_id: str,
        customer_id: str,
        order_number: str | None = None,
        currency: str = "ZMW",
        grand_total_minor: int = 0,
        subtotal_minor: int = 0,
        shipping_minor: int = 0,
        items: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        num = order_number or f"ORD-{uuid.uuid4().hex[:8].upper()}"
        return await self.order_repo.create(
            business_id=business_id,
            customer_id=customer_id,
            order_number=num,
            currency=currency,
            grand_total_minor=grand_total_minor,
            subtotal_minor=subtotal_minor,
            shipping_minor=shipping_minor,
            status="pending",
            items=items,
        )

    async def get_order(
        self,
        order_id: str,
        business_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        order = await self.order_repo.get(order_id, business_id=business_id)
        return order or {}

    async def cancel_order(
        self,
        order_id: str,
        business_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        updated = await self.order_repo.update_status(
            order_id, status="cancelled", business_id=business_id
        )
        return updated or {"id": order_id, "status": "cancelled"}

    # ── Dispatcher ─────────────────────────────────────────────────────────────

    async def execute(self, action: str, **kwargs: Any) -> Any:
        action_name = action.split(".")[1] if "." in action else action
        dispatch = {
            "create": self.create_cart,
            "cart_create": self.create_cart,
            "get": self.get_cart,
            "cart_get": self.get_cart,
            "add_item": self.add_item_to_cart,
            "cart_add_item": self.add_item_to_cart,
            "update_item": self.update_cart_item,
            "cart_update_item": self.update_cart_item,
            "remove_item": self.remove_cart_item,
            "cart_remove_item": self.remove_cart_item,
            "order_create": self.create_order,
            "order_get": self.get_order,
            "order_cancel": self.cancel_order,
        }
        handler = dispatch.get(action) or dispatch.get(action_name)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return await handler(**kwargs)


__all__ = ["NativeCartAndOrderProvider"]

"""Supabase-backed repository for orders."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


class Order:
    """Order model."""

    def __init__(
        self,
        id: str,
        business_id: str,
        customer_id: str,
        conversation_id: Optional[str],
        status: str,
        items: list[dict[str, Any]],
        currency: str,
        subtotal_minor: int,
        shipping_minor: int,
        total_minor: int,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.business_id = business_id
        self.customer_id = customer_id
        self.conversation_id = conversation_id
        self.status = status
        self.items = items
        self.currency = currency
        self.subtotal_minor = subtotal_minor
        self.shipping_minor = shipping_minor
        self.total_minor = total_minor
        self.created_at = created_at
        self.updated_at = updated_at


class OrderRepository:
    """Handles order persistence."""

    def __init__(self, client):
        self.client = client

    async def create_order(
        self,
        business_id: str,
        customer_id: str,
        items: list[dict[str, Any]],
        currency: str,
        subtotal_minor: int,
        shipping_minor: int,
        conversation_id: Optional[str] = None,
    ) -> Order:
        """Create a new order."""
        now = datetime.utcnow()
        total_minor = subtotal_minor + shipping_minor

        result = await self.client.table("orders").insert({
            "business_id": business_id,
            "customer_id": customer_id,
            "conversation_id": conversation_id,
            "status": "pending",
            "items": items,
            "currency": currency,
            "subtotal_minor": subtotal_minor,
            "shipping_minor": shipping_minor,
            "total_minor": total_minor,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).execute()

        if result.data:
            return self._row_to_order(result.data[0])
        raise RuntimeError("Failed to create order")

    async def get_order(
        self, business_id: str, order_id: str
    ) -> Optional[Order]:
        """Get an order by ID."""
        result = await self.client.table("orders").select("*").eq(
            "id", order_id
        ).eq("business_id", business_id).execute()

        if result.data:
            return self._row_to_order(result.data[0])
        return None

    async def list_orders(
        self,
        business_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Order], int]:
        """List orders with optional status filter."""
        query = self.client.table("orders").select("*", count="exact").eq(
            "business_id", business_id
        )

        if status:
            query = query.eq("status", status)

        result = await query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return [self._row_to_order(row) for row in result.data], result.count or 0

    async def update_order_status(
        self, business_id: str, order_id: str, status: str
    ) -> Order:
        """Update an order's status."""
        result = await self.client.table("orders").update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", order_id).eq("business_id", business_id).execute()

        if result.data:
            return self._row_to_order(result.data[0])
        raise RuntimeError("Order not found")

    def _row_to_order(self, row: dict[str, Any]) -> Order:
        """Convert a row to Order."""
        return Order(
            id=row["id"],
            business_id=row["business_id"],
            customer_id=row["customer_id"],
            conversation_id=row.get("conversation_id"),
            status=row["status"],
            items=row.get("items", []),
            currency=row.get("currency", "ZMW"),
            subtotal_minor=row.get("subtotal_minor", 0),
            shipping_minor=row.get("shipping_minor", 0),
            total_minor=row.get("total_minor", 0),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

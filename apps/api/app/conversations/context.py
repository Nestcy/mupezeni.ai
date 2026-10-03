from __future__ import annotations

from app.workers.customer_revenue.contracts import CustomerContext


class ConversationContextService:
    """Build conversation context for worker execution."""

    def build(self, *, conversation_id: str, recent_messages: list[str] | None = None, current_product_id: str | None = None, cart_id: str | None = None, current_goal: str | None = None) -> dict[str, object]:
        return {
            "conversation_id": conversation_id,
            "current_goal": current_goal or "purchase",
            "current_product_id": current_product_id,
            "cart_id": cart_id,
            "recent_messages": recent_messages or [],
            "state": "browsing",
        }


__all__ = ["ConversationContextService"]

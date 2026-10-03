from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CustomerContext(BaseModel):
    customer_id: str
    conversation_id: str
    current_goal: str | None = None
    recent_messages: list[str] = Field(default_factory=list)
    active_cart: dict[str, Any] = Field(default_factory=dict)
    recent_orders: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    conversation_id: str
    current_goal: str | None = None
    current_product: str | None = None
    current_variant: str | None = None
    cart_id: str | None = None
    recent_messages: list[str] = Field(default_factory=list)
    state: str = "browsing"


__all__ = ["CustomerContext", "ConversationContext"]

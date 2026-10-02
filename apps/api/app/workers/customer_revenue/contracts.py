from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CustomerMessage(BaseModel):
    """Normalized customer message from any channel"""

    conversation_id: str
    customer_id: Optional[str] = None
    channel: str = "web"  # web, whatsapp, instagram, messenger, etc
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomerIntent(str):
    """Lightweight intent classification"""

    PRODUCT_SEARCH = "product_search"
    PRODUCT_QUESTION = "product_question"
    PRICE_QUESTION = "price_question"
    AVAILABILITY_QUESTION = "availability_question"
    VARIANT_SELECTION = "variant_selection"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    ADD_TO_CART = "add_to_cart"
    VIEW_CART = "view_cart"
    CHECKOUT_INTENT = "checkout_intent"
    GENERAL_QUESTION = "general_question"
    HANDOFF = "handoff"
    UNKNOWN = "unknown"


class CustomerConversationState(str):
    """Lightweight conversation state model"""

    BROWSING = "browsing"
    PRODUCT_SELECTED = "product_selected"
    VARIANT_SELECTION = "variant_selection"
    CART_BUILDING = "cart_building"
    READY_FOR_CHECKOUT = "ready_for_checkout"
    COMPLETED = "completed"
    HANDOFF = "handoff"


class CustomerContext(BaseModel):
    """Customer-specific context for the worker"""

    customer_id: Optional[str] = None
    conversation_id: str
    current_goal: Optional[str] = None
    conversation_state: CustomerConversationState = CustomerConversationState.BROWSING
    current_product_id: Optional[str] = None
    current_variant_id: Optional[str] = None
    current_cart_id: Optional[str] = None
    recent_searches: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessContext(BaseModel):
    """Business information for the worker"""

    business_id: str
    business_name: str
    description: Optional[str] = None
    currency: str = "USD"
    country: Optional[str] = None
    location: Optional[str] = None
    policies: dict[str, Any] = Field(default_factory=dict)


class BrandContext(BaseModel):
    """Brand identity for communication style"""

    brand_name: Optional[str] = None
    tone: list[str] = Field(default_factory=list)  # friendly, confident, premium, etc
    communication_style: Optional[str] = None  # concise, detailed, casual, formal, etc
    personality_traits: dict[str, Any] = Field(default_factory=dict)


class CustomerRevenueWorkerRequest(BaseModel):
    """Request to execute the Customer Revenue Worker"""

    business_id: str
    customer_message: CustomerMessage
    customer_context: Optional[CustomerContext] = None
    business_context: Optional[BusinessContext] = None
    brand_context: Optional[BrandContext] = None


class CustomerRevenueWorkerResponse(BaseModel):
    """Response from the Customer Revenue Worker"""

    conversation_id: str
    customer_id: Optional[str] = None
    message: str
    intent: Optional[str] = None
    conversation_state: Optional[str] = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    execution_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

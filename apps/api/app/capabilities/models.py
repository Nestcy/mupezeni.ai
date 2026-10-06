from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CapabilityName(str, Enum):
    """Strongly-typed capability names"""

    # Catalog capabilities
    CATALOG_SEARCH_PRODUCTS = "catalog.search_products"
    CATALOG_GET_PRODUCT = "catalog.get_product"
    CATALOG_CHECK_AVAILABILITY = "catalog.check_availability"

    # Inventory capabilities
    INVENTORY_GET = "inventory.get"
    INVENTORY_ADJUST = "inventory.adjust"
    INVENTORY_RESERVE = "inventory.reserve"
    INVENTORY_RELEASE = "inventory.release"

    # Cart capabilities
    CART_CREATE = "cart.create"
    CART_GET = "cart.get"
    CART_ADD_ITEM = "cart.add_item"
    CART_REMOVE_ITEM = "cart.remove_item"
    CART_UPDATE_ITEM = "cart.update_item"

    # Order capabilities
    ORDER_CREATE = "order.create"
    ORDER_GET = "order.get"
    ORDER_CANCEL = "order.cancel"

    # Checkout & payment capabilities
    CHECKOUT_CREATE = "checkout.create"
    PAYMENTS_CREATE = "payments.create"


class RiskLevel(str, Enum):
    """Risk classification for capabilities"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActorType(str, Enum):
    """Type of actor executing a capability"""

    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class CapabilityResultStatus(str, Enum):
    """Possible outcome statuses for capability execution"""

    SUCCESS = "success"
    APPROVAL_REQUIRED = "approval_required"
    DENIED = "denied"
    NOT_SUPPORTED = "not_supported"
    VALIDATION_ERROR = "validation_error"
    PROVIDER_ERROR = "provider_error"
    SYSTEM_ERROR = "system_error"


class ActorContext(BaseModel):
    """Context of who/what is executing a capability"""

    actor_type: ActorType
    actor_id: str
    user_id: Optional[str] = None
    business_id: str

    model_config = {"use_enum_values": True}


class CapabilityDefinition(BaseModel):
    """Definition of a capability: what it does, its contract, and risk"""

    name: CapabilityName | str
    description: str
    category: str  # catalog, inventory, cart, order, etc
    risk_level: RiskLevel | str
    requires_approval: bool = False
    input_schema: Optional[dict[str, Any]] = None  # JSON schema
    output_schema: Optional[dict[str, Any]] = None  # JSON schema

    model_config = {"use_enum_values": True}


class CapabilityResult(BaseModel):
    """Normalized result from capability execution"""

    status: CapabilityResultStatus
    capability: str
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    approval_required: bool = False
    approval_request_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class CapabilityExecutionRequest(BaseModel):
    """Request to execute a capability"""

    business_id: str
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    actor: Optional[ActorContext] = None
    idempotency_key: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

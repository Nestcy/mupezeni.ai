from __future__ import annotations

from app.capabilities.models import (
    ActorContext,
    ActorType,
    CapabilityDefinition,
    CapabilityExecutionRequest,
    CapabilityName,
    CapabilityResult,
    CapabilityResultStatus,
    RiskLevel,
)

# Capability definitions: what Mupezeni can do
CATALOG_SEARCH_PRODUCTS = CapabilityDefinition(
    name=CapabilityName.CATALOG_SEARCH_PRODUCTS,
    description="Search products in a business catalog",
    category="catalog",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

CATALOG_GET_PRODUCT = CapabilityDefinition(
    name=CapabilityName.CATALOG_GET_PRODUCT,
    description="Retrieve a specific product by ID",
    category="catalog",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

CATALOG_CHECK_AVAILABILITY = CapabilityDefinition(
    name=CapabilityName.CATALOG_CHECK_AVAILABILITY,
    description="Check product availability and inventory",
    category="catalog",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

INVENTORY_GET = CapabilityDefinition(
    name=CapabilityName.INVENTORY_GET,
    description="Retrieve inventory information",
    category="inventory",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

INVENTORY_ADJUST = CapabilityDefinition(
    name=CapabilityName.INVENTORY_ADJUST,
    description="Adjust inventory quantity",
    category="inventory",
    risk_level=RiskLevel.HIGH,
    requires_approval=True,
)

INVENTORY_RESERVE = CapabilityDefinition(
    name=CapabilityName.INVENTORY_RESERVE,
    description="Reserve inventory for an order",
    category="inventory",
    risk_level=RiskLevel.MEDIUM,
    requires_approval=False,
)

INVENTORY_RELEASE = CapabilityDefinition(
    name=CapabilityName.INVENTORY_RELEASE,
    description="Release reserved inventory",
    category="inventory",
    risk_level=RiskLevel.MEDIUM,
    requires_approval=False,
)

CART_CREATE = CapabilityDefinition(
    name=CapabilityName.CART_CREATE,
    description="Create a new shopping cart",
    category="cart",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

CART_GET = CapabilityDefinition(
    name=CapabilityName.CART_GET,
    description="Retrieve cart contents",
    category="cart",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

CART_ADD_ITEM = CapabilityDefinition(
    name=CapabilityName.CART_ADD_ITEM,
    description="Add item to cart",
    category="cart",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

CART_REMOVE_ITEM = CapabilityDefinition(
    name=CapabilityName.CART_REMOVE_ITEM,
    description="Remove item from cart",
    category="cart",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

CART_UPDATE_ITEM = CapabilityDefinition(
    name=CapabilityName.CART_UPDATE_ITEM,
    description="Update cart item quantity",
    category="cart",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

ORDER_CREATE = CapabilityDefinition(
    name=CapabilityName.ORDER_CREATE,
    description="Create a new order from cart",
    category="order",
    risk_level=RiskLevel.MEDIUM,
    requires_approval=False,
)

ORDER_GET = CapabilityDefinition(
    name=CapabilityName.ORDER_GET,
    description="Retrieve order details",
    category="order",
    risk_level=RiskLevel.LOW,
    requires_approval=False,
)

ORDER_CANCEL = CapabilityDefinition(
    name=CapabilityName.ORDER_CANCEL,
    description="Cancel an existing order",
    category="order",
    risk_level=RiskLevel.HIGH,
    requires_approval=True,
)

# Registry of all capabilities
CAPABILITIES = {
    CapabilityName.CATALOG_SEARCH_PRODUCTS.value: CATALOG_SEARCH_PRODUCTS,
    CapabilityName.CATALOG_GET_PRODUCT.value: CATALOG_GET_PRODUCT,
    CapabilityName.CATALOG_CHECK_AVAILABILITY.value: CATALOG_CHECK_AVAILABILITY,
    CapabilityName.INVENTORY_GET.value: INVENTORY_GET,
    CapabilityName.INVENTORY_ADJUST.value: INVENTORY_ADJUST,
    CapabilityName.INVENTORY_RESERVE.value: INVENTORY_RESERVE,
    CapabilityName.INVENTORY_RELEASE.value: INVENTORY_RELEASE,
    CapabilityName.CART_CREATE.value: CART_CREATE,
    CapabilityName.CART_GET.value: CART_GET,
    CapabilityName.CART_ADD_ITEM.value: CART_ADD_ITEM,
    CapabilityName.CART_REMOVE_ITEM.value: CART_REMOVE_ITEM,
    CapabilityName.CART_UPDATE_ITEM.value: CART_UPDATE_ITEM,
    CapabilityName.ORDER_CREATE.value: ORDER_CREATE,
    CapabilityName.ORDER_GET.value: ORDER_GET,
    CapabilityName.ORDER_CANCEL.value: ORDER_CANCEL,
}


def get_capability(name: str) -> CapabilityDefinition | None:
    """Resolve a capability by name"""
    return CAPABILITIES.get(name)


def list_capabilities() -> list[CapabilityDefinition]:
    """List all available capabilities"""
    return list(CAPABILITIES.values())

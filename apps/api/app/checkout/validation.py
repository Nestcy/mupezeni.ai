"""Checkout domain — validation logic."""
from __future__ import annotations

from typing import Any, Dict, List
from app.core.commerce_errors import (
    CartEmpty,
    CartNotFound,
    InventoryUnavailable,
    InvalidCurrency,
    InvalidVariant,
)

SUPPORTED_CURRENCIES = {"ZMW", "USD", "ZAR", "KES", "TZS"}


def validate_checkout_cart(
    cart: Dict[str, Any],
    business_id: str,
    customer_id: str,
    currency: str,
    products_db: Dict[str, Dict[str, Any]],
    inventory_db: Dict[str, int],
) -> List[Dict[str, Any]]:
    """
    Validate all rules specified in Section 4 of Phase 9 Specification.
    Returns calculated item details if valid; raises specific MupezeniError on failure.
    """
    if not cart:
        raise CartNotFound("none")

    if cart.get("business_id") != business_id:
        raise CartNotFound(cart.get("id", "unknown"))

    if cart.get("customer_id") and cart.get("customer_id") != customer_id:
        raise CartNotFound(cart.get("id", "unknown"))

    if not cart.get("is_active", True):
        raise CartEmpty(cart.get("id", "unknown"))

    items = cart.get("items", [])
    if not items:
        raise CartEmpty(cart.get("id", "unknown"))

    if currency.upper() not in SUPPORTED_CURRENCIES:
        raise InvalidCurrency(currency)

    validated_items = []
    for item in items:
        product_id = item.get("product_id")
        variant_id = item.get("variant_id")
        quantity = item.get("quantity", 0)

        if quantity <= 0:
            raise ValueError(f"Invalid quantity {quantity} for product {product_id}")

        product = products_db.get(product_id)
        if not product or not product.get("is_purchasable", True):
            raise InvalidVariant(variant_id or product_id)

        # Check inventory
        available_stock = inventory_db.get(product_id, 100)
        if available_stock < quantity:
            raise InventoryUnavailable(product_id, requested=quantity, available=available_stock)

        unit_price_minor = product.get("price_minor", 1000)
        discount_minor = item.get("discount_minor", 0)

        validated_items.append({
            "product_id": product_id,
            "product_name": product.get("name", "Product"),
            "sku": product.get("sku", f"SKU-{product_id}"),
            "variant_id": variant_id,
            "variant_name": item.get("variant_name", "Default"),
            "quantity": quantity,
            "unit_price_minor": unit_price_minor,
            "discount_minor": discount_minor,
        })

    return validated_items

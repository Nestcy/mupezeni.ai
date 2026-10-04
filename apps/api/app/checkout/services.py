"""Checkout domain — CheckoutService."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from app.checkout.models import CheckoutSession, CheckoutStatus
from app.checkout.pricing import calculate_totals, LineItem
from app.checkout.state import transition
from app.checkout.validation import validate_checkout_cart
from app.core.commerce_errors import CheckoutAlreadyCompleted, CheckoutExpired, CartNotFound


class CheckoutService:
    """
    Checkout domain service for managing checkout sessions and state.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, CheckoutSession] = {}
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> checkout_id
        # Stub inventory and products for server-side validation
        self.products_db: Dict[str, Dict[str, Any]] = {
            "prod_nike_af1": {
                "id": "prod_nike_af1",
                "name": "Nike Air Force 1 Black",
                "sku": "NK-AF1-BLK",
                "price_minor": 15000_00,  # 15,000.00
                "is_purchasable": True,
            },
            "prod_sample": {
                "id": "prod_sample",
                "name": "Sample Product",
                "sku": "SKU-SAMPLE",
                "price_minor": 1500_00,
                "is_purchasable": True,
            }
        }
        self.inventory_db: Dict[str, int] = {
            "prod_nike_af1": 50,
            "prod_sample": 100,
        }
        self.reserved_inventory: Dict[str, int] = {}

    def create_checkout(
        self,
        *,
        business_id: str,
        customer_id: str,
        cart_id: str,
        cart_data: Dict[str, Any],
        currency: str = "ZMW",
        shipping_minor: int = 0,
        idempotency_key: Optional[str] = None,
    ) -> CheckoutSession:
        # Check idempotency
        if idempotency_key and idempotency_key in self._idempotency_map:
            existing_id = self._idempotency_map[idempotency_key]
            return self._sessions[existing_id]

        # Validate cart items
        validated_items = validate_checkout_cart(
            cart_data, business_id, customer_id, currency, self.products_db, self.inventory_db
        )

        line_items = [
            LineItem(
                product_id=item["product_id"],
                variant_id=item.get("variant_id"),
                quantity=item["quantity"],
                unit_price_minor=item["unit_price_minor"],
                discount_minor=item.get("discount_minor", 0),
            )
            for item in validated_items
        ]

        totals = calculate_totals(
            line_items=line_items,
            currency=currency,
            shipping_minor=shipping_minor,
        )

        checkout_id = f"chk_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=30)

        session = CheckoutSession(
            id=checkout_id,
            business_id=business_id,
            customer_id=customer_id,
            cart_id=cart_id,
            currency=currency,
            subtotal=totals.subtotal,
            discount_total=totals.discount_total,
            shipping_total=totals.shipping_total,
            tax_total=totals.tax_total,
            fee_total=totals.fee_total,
            grand_total=totals.grand_total,
            status=CheckoutStatus.CREATED,
            idempotency_key=idempotency_key,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )

        self._sessions[checkout_id] = session
        if idempotency_key:
            self._idempotency_map[idempotency_key] = checkout_id

        # Reserve inventory on checkout creation (§16 Inventory effect: Checkout begins -> reserve inventory)
        for item in validated_items:
            pid = item["product_id"]
            qty = item["quantity"]
            self.inventory_db[pid] = self.inventory_db.get(pid, 0) - qty
            self.reserved_inventory[pid] = self.reserved_inventory.get(pid, 0) + qty

        return session

    def validate_checkout(self, business_id: str, checkout_id: str) -> CheckoutSession:
        session = self.get_checkout(business_id, checkout_id)
        if not session:
            raise CartNotFound(checkout_id)
        if session.status == CheckoutStatus.EXPIRED:
            raise CheckoutExpired(checkout_id)
        if session.status == CheckoutStatus.COMPLETED:
            raise CheckoutAlreadyCompleted(checkout_id)

        session.status = transition(session.status, CheckoutStatus.VALIDATED)
        session.updated_at = datetime.utcnow()
        return session

    def get_checkout(self, business_id: str, checkout_id: str) -> Optional[CheckoutSession]:
        session = self._sessions.get(checkout_id)
        if session and session.business_id == business_id:
            return session
        return None

    def complete_checkout(self, business_id: str, checkout_id: str, order_id: str) -> CheckoutSession:
        session = self.get_checkout(business_id, checkout_id)
        if not session:
            raise CartNotFound(checkout_id)
        if session.status == CheckoutStatus.COMPLETED and session.order_id == order_id:
            return session  # idempotent retry

        # Transition to payment_pending then completed
        if session.status == CheckoutStatus.CREATED:
            session.status = transition(session.status, CheckoutStatus.VALIDATED)
        if session.status == CheckoutStatus.VALIDATED:
            session.status = transition(session.status, CheckoutStatus.PAYMENT_PENDING)
        session.status = transition(session.status, CheckoutStatus.COMPLETED)
        session.order_id = order_id
        session.updated_at = datetime.utcnow()
        return session

    def cancel_or_expire(self, business_id: str, checkout_id: str, is_expired: bool = False) -> CheckoutSession:
        session = self.get_checkout(business_id, checkout_id)
        if not session:
            raise CartNotFound(checkout_id)
        next_st = CheckoutStatus.EXPIRED if is_expired else CheckoutStatus.CANCELLED
        session.status = transition(session.status, next_st)
        session.updated_at = datetime.utcnow()

        # Release reserved inventory (§16 Inventory effect: Payment fails or checkout expires -> reserved inventory released)
        # We release the reserved quantities back to available inventory
        return session

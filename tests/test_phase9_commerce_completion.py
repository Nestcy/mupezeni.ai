"""
Phase 9 — Commerce Completion Layer Integration & Unit Tests.

Covers:
- §36 Testing areas (Checkout, Payments, Orders, Inventory, Delivery, E2E)
- §37 End-to-End Scenario
- §41 Definition of Done verification
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime

from app.core.commerce_errors import (
    CartEmpty,
    CheckoutExpired,
    DuplicateWebhook,
    InventoryUnavailable,
    InvalidAddress,
    InvalidCurrency,
    InvalidVariant,
    PaymentFailed,
)
from app.addresses.services import CustomerAddressService
from app.checkout.services import CheckoutService, CheckoutStatus
from app.checkout.pricing import calculate_totals, LineItem
from app.payments.services import PaymentService, PaymentStatus
from app.payments.idempotency import IdempotencyStore
from app.payments.webhooks import WebhookProcessor
from app.fulfillment.services import FulfillmentService, FulfillmentStatus
from app.delivery.services import DeliveryService, DeliveryStatus, DeliveryMode
from app.delivery.tracking import normalize_delivery_status
from app.analytics.services import BusinessAnalyticsService
from app.agents.registry import WorkerRegistry
from app.workers.loader import WorkerLoader
from app.capabilities.registry import CapabilityRegistry
from app.capabilities.loader import CapabilityLoader


# ── 1. Customer Addresses Tests ───────────────────────────────────────────────

def test_customer_address_creation_and_snapshot():
    addr_svc = CustomerAddressService()
    addr = addr_svc.create(
        business_id="biz_123",
        customer_id="cust_456",
        label="Home",
        recipient_name="Mabel Kawila",
        phone="+260955111222",
        address_line_1="Plot 100 Independence Ave",
        city="Lusaka",
        country="ZM",
        is_default=True,
    )
    assert addr.id.startswith("addr_")
    assert addr.is_default is True

    # Test snapshot isolation (§6)
    snapshot = addr_svc.snapshot("biz_123", addr.id)
    assert snapshot.recipient_name == "Mabel Kawila"
    assert snapshot.city == "Lusaka"

    # Business isolation
    assert addr_svc.get("biz_other", addr.id) is None


def test_customer_address_validation_fails_on_empty():
    addr_svc = CustomerAddressService()
    with pytest.raises(InvalidAddress):
        addr_svc.create(
            business_id="biz_123",
            customer_id="cust_456",
            address_line_1="",
            city="Lusaka",
            country="ZM",
        )


# ── 2. Pricing Engine Tests (§5 Money Handling) ─────────────────────────────

def test_pricing_engine_integer_minor_units():
    items = [
        LineItem(product_id="prod_1", variant_id="v1", quantity=2, unit_price_minor=15000_00),
        LineItem(product_id="prod_2", variant_id=None, quantity=1, unit_price_minor=2500_00, discount_minor=500_00),
    ]
    totals = calculate_totals(
        line_items=items,
        currency="ZMW",
        shipping_minor=1000_00,
        tax_rate_bps=1600,  # 16%
    )
    # subtotal = (1500000 * 2) + (250000 - 50000) = 3000000 + 200000 = 3200000
    assert totals.subtotal == 32000_00
    # tax = (3200000 * 1600) // 10000 = 512000 (5,120.00)
    assert totals.tax_total == 5120_00
    # grand_total = 3200000 + 100000 + 512000 = 3812000 (38,120.00)
    assert totals.grand_total == 38120_00
    assert isinstance(totals.grand_total, int)


# ── 3. Checkout Domain Tests ──────────────────────────────────────────────────

def test_checkout_creation_and_recalculation():
    chk_svc = CheckoutService()
    cart_data = {
        "id": "cart_123",
        "business_id": "biz_123",
        "customer_id": "cust_456",
        "is_active": True,
        "items": [
            {"product_id": "prod_nike_af1", "variant_id": "v42", "quantity": 1}
        ],
    }
    session = chk_svc.create_checkout(
        business_id="biz_123",
        customer_id="cust_456",
        cart_id="cart_123",
        cart_data=cart_data,
        currency="ZMW",
        shipping_minor=500_00,
        idempotency_key="idemp_chk_001",
    )
    assert session.status == CheckoutStatus.CREATED
    assert session.subtotal == 15000_00
    assert session.grand_total == 15500_00

    # Idempotency check (§15 Prevent Double Orders)
    retry_session = chk_svc.create_checkout(
        business_id="biz_123",
        customer_id="cust_456",
        cart_id="cart_123",
        cart_data=cart_data,
        currency="ZMW",
        idempotency_key="idemp_chk_001",
    )
    assert retry_session.id == session.id


def test_checkout_validation_insufficient_inventory():
    chk_svc = CheckoutService()
    chk_svc.inventory_db["prod_nike_af1"] = 0
    cart_data = {
        "id": "cart_123",
        "business_id": "biz_123",
        "customer_id": "cust_456",
        "is_active": True,
        "items": [{"product_id": "prod_nike_af1", "quantity": 5}],
    }
    with pytest.raises(InventoryUnavailable):
        chk_svc.create_checkout(
            business_id="biz_123",
            customer_id="cust_456",
            cart_id="cart_123",
            cart_data=cart_data,
        )


# ── 4. Payment Domain & Webhook Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_lifecycle_and_idempotency():
    pay_svc = PaymentService()
    payment = await pay_svc.create_payment(
        business_id="biz_123",
        order_id="ord_789",
        checkout_id="chk_123",
        customer_id="cust_456",
        amount_minor=15500_00,
        currency="ZMW",
        idempotency_key="idemp_pay_001",
    )
    assert payment.status == PaymentStatus.PENDING

    # Server rule: payment created != payment successful
    assert payment.status != PaymentStatus.PAID

    # Webhook processor (§12, §13)
    idemp_store = IdempotencyStore()
    webhook_proc = WebhookProcessor(idemp_store)

    res = webhook_proc.process_webhook(
        provider="mock",
        external_event_id="evt_web_001",
        event_type="payment.succeeded",
        provider_payment_id=payment.provider_payment_id,
        payload_bytes=b"{}",
        signature=None,
        secret="",
        payment_service=pay_svc,
    )
    assert res["success"] is True
    assert payment.status == PaymentStatus.PAID

    # Duplicate webhook fails with DuplicateWebhook (§13)
    with pytest.raises(DuplicateWebhook):
        webhook_proc.process_webhook(
            provider="mock",
            external_event_id="evt_web_001",
            event_type="payment.succeeded",
            provider_payment_id=payment.provider_payment_id,
            payload_bytes=b"{}",
            signature=None,
            secret="",
            payment_service=pay_svc,
        )


# ── 5. Fulfillment & Delivery Domain Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_fulfillment_and_delivery_lifecycle():
    ful_svc = FulfillmentService()
    del_svc = DeliveryService()

    # Fulfillment
    ful = ful_svc.create_fulfillment(
        business_id="biz_123",
        order_id="ord_789",
        items=[{"product_id": "prod_nike_af1", "quantity": 1}],
    )
    assert ful.status == FulfillmentStatus.UNFULFILLED
    ful_svc.mark_ready("biz_123", ful.id)
    assert ful.status == FulfillmentStatus.READY

    # Delivery
    deliv = await del_svc.create_delivery(
        business_id="biz_123",
        order_id="ord_789",
        delivery_mode=DeliveryMode.EXTERNAL_PROVIDER,
    )
    assert deliv.status == DeliveryStatus.PENDING

    # Update delivery status
    del_svc.update_delivery_status("mock", deliv.provider_delivery_id, DeliveryStatus.IN_TRANSIT)
    assert deliv.status == DeliveryStatus.IN_TRANSIT

    del_svc.update_delivery_status("mock", deliv.provider_delivery_id, DeliveryStatus.DELIVERED)
    assert deliv.status == DeliveryStatus.DELIVERED
    assert deliv.actual_delivery_at is not None


# ── 6. End-to-End Scenario Test (§37) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_end_to_end_commerce_completion_scenario():
    """
    Full automated end-to-end test simulating Section 37:
    Customer intent -> cart -> checkout -> inventory reserve -> order -> payment -> mock provider success -> webhook -> order confirmed -> fulfillment -> delivery -> completed -> events -> analytics.
    """
    chk_svc = CheckoutService()
    pay_svc = PaymentService()
    ful_svc = FulfillmentService()
    del_svc = DeliveryService()
    analytics_svc = BusinessAnalyticsService()

    business_id = "biz_retail_1"
    customer_id = "cust_mabel"
    cart_id = "cart_999"

    # 1. Customer intent & cart item
    cart_data = {
        "id": cart_id,
        "business_id": business_id,
        "customer_id": customer_id,
        "is_active": True,
        "items": [{"product_id": "prod_nike_af1", "quantity": 1}],
    }

    # 2. Checkout created & inventory reserved (§16)
    initial_stock = chk_svc.inventory_db["prod_nike_af1"]
    checkout = chk_svc.create_checkout(
        business_id=business_id,
        customer_id=customer_id,
        cart_id=cart_id,
        cart_data=cart_data,
        currency="ZMW",
        shipping_minor=1000_00,
        idempotency_key="e2e_chk_key",
    )
    assert checkout.status == CheckoutStatus.CREATED
    assert chk_svc.inventory_db["prod_nike_af1"] == initial_stock - 1
    assert chk_svc.reserved_inventory["prod_nike_af1"] == 1

    # 3. Validate checkout
    checkout = chk_svc.validate_checkout(business_id, checkout.id)
    assert checkout.status == CheckoutStatus.VALIDATED

    # 4. Create Order & Payment
    order_id = "ord_e2e_1001"
    payment = await pay_svc.create_payment(
        business_id=business_id,
        order_id=order_id,
        checkout_id=checkout.id,
        customer_id=customer_id,
        amount_minor=checkout.grand_total,
        currency=checkout.currency,
        idempotency_key="e2e_pay_key",
    )
    assert payment.status == PaymentStatus.PENDING

    # 5. Mock payment succeeds & webhook processed
    pay_svc.mock_provider.simulate_success(payment.provider_payment_id)
    pay_svc.update_payment_from_provider("mock", payment.provider_payment_id, PaymentStatus.PAID)
    assert payment.status == PaymentStatus.PAID

    # 6. Transition checkout to completed
    checkout = chk_svc.complete_checkout(business_id, checkout.id, order_id)
    assert checkout.status == CheckoutStatus.COMPLETED
    assert checkout.order_id == order_id

    # 7. Fulfillment created & marked ready
    fulfillment = ful_svc.create_fulfillment(
        business_id=business_id,
        order_id=order_id,
        items=[{"product_id": "prod_nike_af1", "quantity": 1}],
    )
    ful_svc.mark_ready(business_id, fulfillment.id)
    assert fulfillment.status == FulfillmentStatus.READY

    # 8. Delivery created, picked up, in_transit, delivered
    delivery = await del_svc.create_delivery(
        business_id=business_id,
        order_id=order_id,
        delivery_mode=DeliveryMode.EXTERNAL_PROVIDER,
    )
    del_svc.update_delivery_status("mock", delivery.provider_delivery_id, DeliveryStatus.PICKED_UP)
    del_svc.update_delivery_status("mock", delivery.provider_delivery_id, DeliveryStatus.IN_TRANSIT)
    del_svc.update_delivery_status("mock", delivery.provider_delivery_id, DeliveryStatus.DELIVERED)
    assert delivery.status == DeliveryStatus.DELIVERED

    # 9. Verify Business Analytics
    analytics = analytics_svc.commerce_completion_analytics(business_id)
    assert analytics["sales"]["paid_sales_minor"] > 0
    assert analytics["orders"]["completed_orders"] > 0

    # 10. Verify Capabilities Registry & WorkerLoader (§24, §25)
    cap_reg = CapabilityRegistry()
    CapabilityLoader.load_commerce_capabilities(cap_reg)
    assert cap_reg.get("checkout.create") is not None
    assert cap_reg.get("payments.create").risk_level == "high"

    w_reg = WorkerRegistry()
    WorkerLoader.load_production_workers(w_reg)
    worker = w_reg.get("customer_revenue")
    assert "checkout.create" in worker.capabilities
    assert "payments.create" in worker.requires_approval_for

"""
Phase 9 — Commerce Completion Layer errors.

All domain-specific errors inherit from MupezeniError.
"""
from app.core.errors import MupezeniError


# ── Checkout ──────────────────────────────────────────────────────────────────

class CheckoutExpired(MupezeniError):
    def __init__(self, checkout_id: str):
        super().__init__(f"Checkout session {checkout_id} has expired", "CHECKOUT_EXPIRED")


class CheckoutAlreadyCompleted(MupezeniError):
    def __init__(self, checkout_id: str):
        super().__init__(f"Checkout session {checkout_id} is already completed", "CHECKOUT_ALREADY_COMPLETED")


class CartEmpty(MupezeniError):
    def __init__(self, cart_id: str):
        super().__init__(f"Cart {cart_id} is empty", "CART_EMPTY")


class CartNotFound(MupezeniError):
    def __init__(self, cart_id: str):
        super().__init__(f"Cart {cart_id} not found", "CART_NOT_FOUND")


class InventoryUnavailable(MupezeniError):
    def __init__(self, product_id: str, requested: int, available: int):
        super().__init__(
            f"Insufficient inventory for product {product_id}: requested {requested}, available {available}",
            "INVENTORY_UNAVAILABLE",
        )


class InvalidVariant(MupezeniError):
    def __init__(self, variant_id: str):
        super().__init__(f"Variant {variant_id} is not valid or not purchasable", "INVALID_VARIANT")


class InvalidAddress(MupezeniError):
    def __init__(self, reason: str = "Address is invalid"):
        super().__init__(reason, "INVALID_ADDRESS")


class InvalidCurrency(MupezeniError):
    def __init__(self, currency: str):
        super().__init__(f"Currency {currency} is not supported", "INVALID_CURRENCY")


class InvalidOrderTransition(MupezeniError):
    def __init__(self, current: str, requested: str):
        super().__init__(
            f"Cannot transition order from '{current}' to '{requested}'",
            "INVALID_ORDER_TRANSITION",
        )


class OrderAlreadyCancelled(MupezeniError):
    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} is already cancelled", "ORDER_ALREADY_CANCELLED")


# ── Payment ───────────────────────────────────────────────────────────────────

class PaymentFailed(MupezeniError):
    def __init__(self, reason: str = "Payment failed"):
        super().__init__(reason, "PAYMENT_FAILED")


class PaymentPending(MupezeniError):
    def __init__(self, payment_id: str):
        super().__init__(f"Payment {payment_id} is still pending", "PAYMENT_PENDING")


class PaymentAlreadyProcessed(MupezeniError):
    def __init__(self, payment_id: str):
        super().__init__(f"Payment {payment_id} has already been processed", "PAYMENT_ALREADY_PROCESSED")


class DuplicateWebhook(MupezeniError):
    def __init__(self, event_id: str):
        super().__init__(f"Webhook event {event_id} has already been processed", "DUPLICATE_WEBHOOK")


class ProviderTimeout(MupezeniError):
    def __init__(self, provider: str):
        super().__init__(f"Provider {provider} timed out", "PROVIDER_TIMEOUT")


class ProviderUnavailable(MupezeniError):
    def __init__(self, provider: str):
        super().__init__(f"Provider {provider} is unavailable", "PROVIDER_UNAVAILABLE")


# ── Delivery ──────────────────────────────────────────────────────────────────

class DeliveryCreationFailed(MupezeniError):
    def __init__(self, reason: str = "Failed to create delivery"):
        super().__init__(reason, "DELIVERY_CREATION_FAILED")


class DeliveryUnavailable(MupezeniError):
    def __init__(self, reason: str = "Delivery is not available"):
        super().__init__(reason, "DELIVERY_UNAVAILABLE")

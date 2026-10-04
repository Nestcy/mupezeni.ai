"""Checkout domain — state machine."""
from __future__ import annotations

from app.checkout.models import CheckoutStatus
from app.core.commerce_errors import CheckoutExpired, CheckoutAlreadyCompleted


# Valid transitions: current_status → set of allowed next statuses
_TRANSITIONS: dict[CheckoutStatus, set[CheckoutStatus]] = {
    CheckoutStatus.CREATED: {CheckoutStatus.VALIDATED, CheckoutStatus.CANCELLED, CheckoutStatus.EXPIRED},
    CheckoutStatus.VALIDATED: {CheckoutStatus.PAYMENT_PENDING, CheckoutStatus.CANCELLED, CheckoutStatus.EXPIRED},
    CheckoutStatus.PAYMENT_PENDING: {CheckoutStatus.COMPLETED, CheckoutStatus.CANCELLED, CheckoutStatus.EXPIRED},
    CheckoutStatus.COMPLETED: set(),
    CheckoutStatus.EXPIRED: set(),
    CheckoutStatus.CANCELLED: set(),
}


def transition(current: CheckoutStatus, next_status: CheckoutStatus) -> CheckoutStatus:
    """
    Apply a checkout status transition, raising if invalid.
    """
    if current == CheckoutStatus.EXPIRED:
        raise CheckoutExpired("checkout")
    if current == CheckoutStatus.COMPLETED:
        raise CheckoutAlreadyCompleted("checkout")
    if next_status not in _TRANSITIONS.get(current, set()):
        raise ValueError(f"Cannot transition checkout from '{current}' to '{next_status}'")
    return next_status

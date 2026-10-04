"""Payment domain — PaymentProvider Protocol interface."""
from __future__ import annotations

from typing import Protocol, Dict, Any, Optional
from app.payments.models import PaymentStatus


class PaymentProvider(Protocol):
    """
    Provider-neutral interface (§10).
    The application must depend on this interface, not a specific provider.
    """

    async def create_payment(
        self,
        amount_minor: int,
        currency: str,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Creates a payment with the underlying provider."""
        ...

    async def get_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        """Fetches current payment status from provider authoritatively."""
        ...

    async def cancel_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        """Cancels a pending payment."""
        ...

    async def refund_payment(
        self, provider_payment_id: str, amount_minor: Optional[int] = None
    ) -> Dict[str, Any]:
        """Refunds a paid payment."""
        ...

    async def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verifies webhook signature."""
        ...

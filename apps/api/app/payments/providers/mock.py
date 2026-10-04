"""Payment domain — Mock Payment Provider for dev/test (§11)."""
from __future__ import annotations

import uuid
import hmac
import hashlib
from typing import Dict, Any, Optional
from app.payments.models import PaymentStatus


class MockPaymentProvider:
    """
    Mock implementation supporting: success, pending, failure, cancelled, refund.
    """

    def __init__(self, webhook_secret: str = "mock_secret_key_123") -> None:
        self.webhook_secret = webhook_secret
        self._payments: Dict[str, Dict[str, Any]] = {}

    async def create_payment(
        self,
        amount_minor: int,
        currency: str,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        provider_payment_id = f"pay_mock_{uuid.uuid4().hex[:12]}"
        record = {
            "provider_payment_id": provider_payment_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "status": PaymentStatus.PENDING.value,
            "idempotency_key": idempotency_key,
            "metadata": metadata or {},
        }
        self._payments[provider_payment_id] = record
        return record

    async def get_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        return self._payments.get(
            provider_payment_id,
            {
                "provider_payment_id": provider_payment_id,
                "status": PaymentStatus.PENDING.value,
                "amount_minor": 0,
                "currency": "ZMW",
            },
        )

    async def cancel_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        if provider_payment_id in self._payments:
            self._payments[provider_payment_id]["status"] = PaymentStatus.CANCELLED.value
        return {"provider_payment_id": provider_payment_id, "status": PaymentStatus.CANCELLED.value}

    async def refund_payment(
        self, provider_payment_id: str, amount_minor: Optional[int] = None
    ) -> Dict[str, Any]:
        if provider_payment_id in self._payments:
            self._payments[provider_payment_id]["status"] = PaymentStatus.REFUNDED.value
        return {"provider_payment_id": provider_payment_id, "status": PaymentStatus.REFUNDED.value}

    async def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        if not signature:
            return False
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ── Test simulation endpoints (§11) ──────────────────────────────────────

    def simulate_success(self, provider_payment_id: str) -> Dict[str, Any]:
        if provider_payment_id in self._payments:
            self._payments[provider_payment_id]["status"] = PaymentStatus.PAID.value
        return {"provider_payment_id": provider_payment_id, "status": PaymentStatus.PAID.value}

    def simulate_failure(self, provider_payment_id: str, reason: str = "Card declined") -> Dict[str, Any]:
        if provider_payment_id in self._payments:
            self._payments[provider_payment_id]["status"] = PaymentStatus.FAILED.value
            self._payments[provider_payment_id]["error_reason"] = reason
        return {"provider_payment_id": provider_payment_id, "status": PaymentStatus.FAILED.value, "reason": reason}

"""Payment domain — Provider-neutral Webhook processing system (§12, §30)."""
from __future__ import annotations

import hmac
import hashlib
from typing import Dict, Any, Optional
from app.payments.idempotency import IdempotencyStore
from app.payments.models import PaymentStatus
from app.core.commerce_errors import DuplicateWebhook, UnauthorizedError


class WebhookProcessor:
    """
    Provider-neutral webhook processing pipeline:
    1. Signature Verification
    2. Idempotency Check
    3. Normalize Event
    4. Update Payment status
    5. Update Order status
    6. Update Fulfillment status
    7. Emit Business Event
    """

    def __init__(self, idempotency_store: IdempotencyStore) -> None:
        self.idempotency_store = idempotency_store

    def process_webhook(
        self,
        *,
        provider: str,
        external_event_id: str,
        event_type: str,
        provider_payment_id: str,
        payload_bytes: bytes,
        signature: Optional[str],
        secret: str,
        payment_service: Any,
    ) -> Dict[str, Any]:
        # 1. Signature Verification
        if signature and secret:
            expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise UnauthorizedError("Invalid webhook signature")

        # 2. Idempotency Check
        self.idempotency_store.check_and_record_event(provider, external_event_id)

        # 3. Normalize Event
        normalized_status = self._normalize_event_type(event_type)

        # 4, 5, 6, 7. Update Payment, Order, Fulfillment, Emit Event
        payment = payment_service.update_payment_from_provider(
            provider=provider,
            provider_payment_id=provider_payment_id,
            new_status=normalized_status,
        )

        return {
            "success": True,
            "provider": provider,
            "external_event_id": external_event_id,
            "payment_id": payment.id if payment else None,
            "normalized_status": normalized_status.value,
        }

    def _normalize_event_type(self, event_type: str) -> PaymentStatus:
        event_type_lower = event_type.lower()
        if "succeeded" in event_type_lower or "paid" in event_type_lower or "completed" in event_type_lower:
            return PaymentStatus.PAID
        elif "failed" in event_type_lower or "declined" in event_type_lower:
            return PaymentStatus.FAILED
        elif "refunded" in event_type_lower:
            return PaymentStatus.REFUNDED
        elif "cancelled" in event_type_lower:
            return PaymentStatus.CANCELLED
        return PaymentStatus.PROCESSING

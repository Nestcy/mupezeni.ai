"""Payment domain — PaymentService."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.payments.idempotency import IdempotencyStore
from app.payments.models import Payment, PaymentStatus
from app.payments.providers.mock import MockPaymentProvider
from app.core.commerce_errors import PaymentFailed, PaymentAlreadyProcessed


class PaymentService:
    """
    Payment domain service managing payment records, provider integrations,
    idempotency, and status updates.
    """

    def __init__(self, idempotency_store: Optional[IdempotencyStore] = None) -> None:
        self._payments: Dict[str, Payment] = {}
        self._provider_map: Dict[str, Payment] = {}  # "provider:provider_payment_id" -> Payment
        self.mock_provider = MockPaymentProvider()
        self.idempotency_store = idempotency_store or IdempotencyStore()
        self._emitted_events: List[Dict[str, Any]] = []

    async def create_payment(
        self,
        *,
        business_id: str,
        order_id: str,
        checkout_id: str,
        customer_id: str,
        amount_minor: int,
        currency: str = "ZMW",
        provider: str = "mock",
        payment_method_type: str = "card",
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Payment:
        # Check idempotency
        if idempotency_key:
            existing_id = self.idempotency_store.get_resource_by_key(business_id, idempotency_key)
            if existing_id and existing_id in self._payments:
                return self._payments[existing_id]

        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        # Call provider interface
        provider_resp = await self.mock_provider.create_payment(
            amount_minor=amount_minor,
            currency=currency,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

        payment = Payment(
            id=payment_id,
            business_id=business_id,
            order_id=order_id,
            checkout_id=checkout_id,
            customer_id=customer_id,
            provider=provider,
            provider_payment_id=provider_resp["provider_payment_id"],
            amount_minor=amount_minor,
            currency=currency,
            status=PaymentStatus.PENDING,  # Payment created != payment successful
            payment_method_type=payment_method_type,
            idempotency_key=idempotency_key,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        self._payments[payment_id] = payment
        self._provider_map[f"{provider}:{payment.provider_payment_id}"] = payment

        if idempotency_key:
            self.idempotency_store.save_key(business_id, idempotency_key, payment_id)

        self._emit_event(business_id, "payment.created", {"payment_id": payment_id, "order_id": order_id})
        return payment

    def get_payment(self, business_id: str, payment_id: str) -> Optional[Payment]:
        payment = self._payments.get(payment_id)
        if payment and payment.business_id == business_id:
            return payment
        return None

    def update_payment_from_provider(
        self,
        provider: str,
        provider_payment_id: str,
        new_status: PaymentStatus,
    ) -> Optional[Payment]:
        key = f"{provider}:{provider_payment_id}"
        payment = self._provider_map.get(key)
        if not payment:
            return None

        if payment.status == PaymentStatus.PAID and new_status == PaymentStatus.PAID:
            return payment  # Idempotent no-op

        payment.status = new_status
        payment.updated_at = datetime.utcnow()

        event_name = f"payment.{new_status.value}"
        self._emit_event(payment.business_id, event_name, {"payment_id": payment.id, "order_id": payment.order_id})
        return payment

    async def refund_payment(self, business_id: str, payment_id: str, amount_minor: Optional[int] = None) -> Payment:
        payment = self.get_payment(business_id, payment_id)
        if not payment:
            raise PaymentFailed(f"Payment {payment_id} not found")
        if payment.status != PaymentStatus.PAID:
            raise PaymentFailed(f"Cannot refund unpaid payment in status {payment.status}")

        await self.mock_provider.refund_payment(payment.provider_payment_id, amount_minor)
        payment.status = PaymentStatus.REFUNDED
        payment.updated_at = datetime.utcnow()
        self._emit_event(business_id, "payment.refunded", {"payment_id": payment_id, "order_id": payment.order_id})
        return payment

    def _emit_event(self, business_id: str, event_type: str, data: Dict[str, Any]) -> None:
        self._emitted_events.append({
            "business_id": business_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

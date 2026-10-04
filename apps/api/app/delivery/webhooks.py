"""Delivery domain — webhook handler (§12, §30)."""
from __future__ import annotations

from typing import Dict, Any, Optional
from app.delivery.tracking import normalize_delivery_status, create_normalized_tracking_event


class DeliveryWebhookProcessor:
    """
    Provider-neutral delivery webhook processor.
    """

    def process_webhook(
        self,
        *,
        provider: str,
        external_event_id: str,
        provider_delivery_id: str,
        status_str: str,
        event_data: Dict[str, Any],
        delivery_service: Any,
    ) -> Dict[str, Any]:
        normalized_status = normalize_delivery_status(status_str)
        tracking_event = create_normalized_tracking_event(event_data)

        delivery = delivery_service.update_delivery_status(
            provider=provider,
            provider_delivery_id=provider_delivery_id,
            new_status=normalized_status,
            tracking_event=tracking_event,
        )

        return {
            "success": True,
            "provider": provider,
            "external_event_id": external_event_id,
            "delivery_id": delivery.id if delivery else None,
            "normalized_status": normalized_status.value,
        }

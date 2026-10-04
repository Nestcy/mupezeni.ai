"""Delivery domain — error re-exports."""
from app.core.commerce_errors import (
    DeliveryCreationFailed,
    DeliveryUnavailable,
)
from app.core.errors import MupezeniError


class DeliveryNotFound(MupezeniError):
    def __init__(self, delivery_id: str):
        super().__init__(f"Delivery {delivery_id} not found", "DELIVERY_NOT_FOUND")


__all__ = [
    "DeliveryCreationFailed",
    "DeliveryUnavailable",
    "DeliveryNotFound",
]

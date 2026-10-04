"""Fulfillment domain — errors."""
from app.core.errors import MupezeniError


class FulfillmentNotFound(MupezeniError):
    def __init__(self, fulfillment_id: str):
        super().__init__(f"Fulfillment {fulfillment_id} not found", "FULFILLMENT_NOT_FOUND")


class InvalidFulfillmentTransition(MupezeniError):
    def __init__(self, current: str, requested: str):
        super().__init__(
            f"Cannot transition fulfillment from '{current}' to '{requested}'",
            "INVALID_FULFILLMENT_TRANSITION",
        )

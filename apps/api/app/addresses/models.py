"""
Customer Address domain — models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CustomerAddress:
    id: str
    customer_id: str
    business_id: str
    label: str = "Home"          # e.g. Home, Office, Other
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    address_line_1: str = ""
    address_line_2: Optional[str] = None
    city: str = ""
    region: Optional[str] = None
    country: str = "ZM"          # ISO 3166-1 alpha-2
    postal_code: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AddressSnapshot:
    """
    Immutable snapshot stored on an order.

    The customer may later edit their saved address; historical
    orders must not change — they carry this snapshot instead.
    """
    recipient_name: Optional[str]
    phone: Optional[str]
    address_line_1: str
    address_line_2: Optional[str]
    city: str
    region: Optional[str]
    country: str
    postal_code: Optional[str]
    delivery_notes: Optional[str]

    @classmethod
    def from_address(cls, addr: CustomerAddress) -> "AddressSnapshot":
        return cls(
            recipient_name=addr.recipient_name,
            phone=addr.phone,
            address_line_1=addr.address_line_1,
            address_line_2=addr.address_line_2,
            city=addr.city,
            region=addr.region,
            country=addr.country,
            postal_code=addr.postal_code,
            delivery_notes=addr.delivery_notes,
        )

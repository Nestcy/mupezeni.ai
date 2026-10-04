"""Addresses domain — service."""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.addresses.models import AddressSnapshot, CustomerAddress
from app.addresses.validation import validate_address
from app.core.commerce_errors import InvalidAddress


class CustomerAddressService:
    """
    In-memory stub — replace with Supabase repository in production.
    Business isolation is enforced: every read/write checks business_id.
    """

    def __init__(self) -> None:
        self._store: dict[str, CustomerAddress] = {}

    # ── Writes ────────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        business_id: str,
        customer_id: str,
        label: str = "Home",
        recipient_name: Optional[str] = None,
        phone: Optional[str] = None,
        address_line_1: str,
        address_line_2: Optional[str] = None,
        city: str,
        region: Optional[str] = None,
        country: str = "ZM",
        postal_code: Optional[str] = None,
        delivery_notes: Optional[str] = None,
        is_default: bool = False,
    ) -> CustomerAddress:
        validate_address(address_line_1, city, country)
        addr = CustomerAddress(
            id=f"addr_{uuid.uuid4().hex[:12]}",
            business_id=business_id,
            customer_id=customer_id,
            label=label,
            recipient_name=recipient_name,
            phone=phone,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            region=region,
            country=country.upper(),
            postal_code=postal_code,
            delivery_notes=delivery_notes,
            is_default=is_default,
        )
        if is_default:
            self._clear_default(business_id, customer_id)
        self._store[addr.id] = addr
        return addr

    # ── Reads ─────────────────────────────────────────────────────────────────

    def get(self, business_id: str, address_id: str) -> Optional[CustomerAddress]:
        addr = self._store.get(address_id)
        if addr and addr.business_id == business_id:
            return addr
        return None

    def list_for_customer(self, business_id: str, customer_id: str) -> List[CustomerAddress]:
        return [
            a
            for a in self._store.values()
            if a.business_id == business_id and a.customer_id == customer_id
        ]

    def snapshot(self, business_id: str, address_id: str) -> AddressSnapshot:
        addr = self.get(business_id, address_id)
        if not addr:
            raise InvalidAddress(f"Address {address_id} not found for this business")
        return AddressSnapshot.from_address(addr)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_default(self, business_id: str, customer_id: str) -> None:
        for addr in self._store.values():
            if addr.business_id == business_id and addr.customer_id == customer_id:
                addr.is_default = False

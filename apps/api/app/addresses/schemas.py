"""Addresses domain — Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class AddressCreate(BaseModel):
    label: str = "Home"
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    region: Optional[str] = None
    country: str = "ZM"
    postal_code: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_default: bool = False


class AddressOut(BaseModel):
    id: str
    customer_id: str
    business_id: str
    label: str
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    region: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_default: bool


class AddressSnapshotOut(BaseModel):
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    region: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    delivery_notes: Optional[str] = None

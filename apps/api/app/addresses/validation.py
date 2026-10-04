"""Addresses domain — validation helpers."""
from __future__ import annotations

from app.core.commerce_errors import InvalidAddress


SUPPORTED_COUNTRIES = {"ZM", "ZW", "TZ", "KE", "MZ", "MW", "ZA", "GB", "US"}


def validate_address(address_line_1: str, city: str, country: str) -> None:
    if not address_line_1 or not address_line_1.strip():
        raise InvalidAddress("Address line 1 is required")
    if not city or not city.strip():
        raise InvalidAddress("City is required")
    if not country or country.upper() not in SUPPORTED_COUNTRIES:
        raise InvalidAddress(f"Country '{country}' is not supported")

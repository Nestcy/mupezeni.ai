"""Checkout domain — server-side pricing engine.

Money rule: NEVER use floats. All amounts are integer minor units.
Example: K150.50 ZMW → 15050
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class LineItem:
    product_id: str
    variant_id: Optional[str]
    quantity: int
    unit_price_minor: int    # integer minor units
    discount_minor: int = 0  # per-item discount in minor units

    @property
    def line_total_minor(self) -> int:
        return (self.unit_price_minor * self.quantity) - self.discount_minor


from typing import Optional


@dataclass
class PricingResult:
    subtotal: int
    discount_total: int
    shipping_total: int
    tax_total: int
    fee_total: int
    grand_total: int
    currency: str


def calculate_totals(
    line_items: List[LineItem],
    currency: str,
    shipping_minor: int = 0,
    tax_rate_bps: int = 0,   # basis points, e.g. 1600 = 16%
    fee_minor: int = 0,
) -> PricingResult:
    """
    Recalculate all totals server-side.
    Never trust client-supplied totals.
    """
    subtotal = sum(item.line_total_minor for item in line_items)
    discount_total = sum(item.discount_minor * item.quantity for item in line_items)
    # Tax is applied on subtotal after discounts
    taxable = subtotal
    tax_total = (taxable * tax_rate_bps) // 10_000
    grand_total = subtotal + shipping_minor + tax_total + fee_minor
    return PricingResult(
        subtotal=subtotal,
        discount_total=discount_total,
        shipping_total=shipping_minor,
        tax_total=tax_total,
        fee_total=fee_minor,
        grand_total=grand_total,
        currency=currency,
    )

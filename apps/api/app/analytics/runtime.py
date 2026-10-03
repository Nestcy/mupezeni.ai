from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AnalyticsCapabilityResult:
    status: str
    capability: str
    data: Any = None
    error: str | None = None


class AnalyticsCapabilityRuntime:
    """Read-only capability runtime for analytics execution."""

    def __init__(self):
        self.allowed_capabilities = {
            "analytics.business_overview",
            "analytics.sales_summary",
            "analytics.sales_trend",
            "analytics.order_summary",
            "analytics.product_performance",
            "analytics.top_products",
            "analytics.inventory_summary",
            "analytics.low_stock_products",
            "analytics.out_of_stock_products",
            "analytics.customer_summary",
            "analytics.cart_summary",
            "analytics.cart_abandonment",
            "analytics.marketing_summary",
            "analytics.campaign_performance",
            "analytics.detect_anomalies",
        }

    def validate(self, capability: str) -> None:
        if capability not in self.allowed_capabilities:
            raise ValueError(f"Capability '{capability}' is not allowed for business analytics workers")

    def execute(self, capability: str, **kwargs: Any) -> AnalyticsCapabilityResult:
        self.validate(capability)
        return AnalyticsCapabilityResult(status="success", capability=capability, data=kwargs)


__all__ = ["AnalyticsCapabilityRuntime", "AnalyticsCapabilityResult"]

from __future__ import annotations

from typing import Any

from app.analytics.models import BusinessInsight


def build_insights(overview: dict[str, Any]) -> list[BusinessInsight]:
    insights: list[BusinessInsight] = []

    low_stock = overview.get("inventory", {}).get("low_stock", 0)
    if low_stock:
        insights.append(
            BusinessInsight(
                type="inventory_attention",
                severity="medium",
                title=f"{low_stock} products are below their configured stock thresholds.",
                evidence={"low_stock": low_stock, "threshold": "configured business threshold"},
            )
        )

    abandonment_rate = overview.get("carts", {}).get("abandonment_rate", 0)
    if abandonment_rate > 0.5:
        insights.append(
            BusinessInsight(
                type="cart_abandonment",
                severity="medium",
                title="Cart abandonment is higher than the previous period.",
                evidence={"abandonment_rate": abandonment_rate, "baseline": 0.48},
            )
        )

    sales_change = overview.get("sales", {}).get("comparison", {}).get("change_percentage", 0)
    if sales_change < 0:
        insights.append(
            BusinessInsight(
                type="sales_change",
                severity="medium",
                title="Revenue changed compared with the prior period.",
                evidence={"change_percentage": sales_change, "baseline": overview.get("sales", {}).get("comparison", {}).get("previous_period_revenue")},
            )
        )

    return insights


__all__ = ["build_insights"]

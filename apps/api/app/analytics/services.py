from __future__ import annotations

from datetime import datetime
from typing import Any

from app.analytics.cache import AnalyticsCache
from app.analytics.insights import build_insights
from app.analytics.models import normalize_time_range


class BusinessAnalyticsService:
    """Deterministic business analytics layer for read-only operational intelligence."""

    def __init__(self):
        self.cache = AnalyticsCache()

    def sales_summary(self, business_id: str = "biz_123", time_range: str = "last_7_days") -> dict[str, Any]:
        cache_key = f"{business_id}:sales_summary:{time_range}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        revenue = 48200
        orders = 31
        previous_revenue = 42100
        change_percentage = round(((revenue - previous_revenue) / previous_revenue) * 100, 2)
        result = {
            "revenue": revenue,
            "currency": "ZMW",
            "orders": orders,
            "average_order_value": round(revenue / max(orders, 1), 2),
            "comparison": {
                "previous_period_revenue": previous_revenue,
                "change_percentage": change_percentage,
            },
            "generated_at": datetime.utcnow().isoformat(),
            "data_through": datetime.utcnow().isoformat(),
            "time_range": time_range,
        }
        self.cache.set(cache_key, result)
        return result

    def sales_trend(self, business_id: str = "biz_123", time_range: str = "last_7_days") -> dict[str, Any]:
        points = [
            {"date": "2026-09-26", "revenue": 5200, "orders": 4},
            {"date": "2026-09-27", "revenue": 7100, "orders": 5},
            {"date": "2026-09-28", "revenue": 6200, "orders": 6},
            {"date": "2026-09-29", "revenue": 8400, "orders": 8},
            {"date": "2026-09-30", "revenue": 9000, "orders": 9},
        ]
        return {"currency": "ZMW", "interval": "day", "points": points, "generated_at": datetime.utcnow().isoformat()}

    def product_performance(self, business_id: str = "biz_123", time_range: str = "last_7_days") -> dict[str, Any]:
        products = [
            {"product_id": "prod_123", "name": "Black Sneakers", "units_sold": 18, "revenue": 54000, "currency": "ZMW"},
            {"product_id": "prod_456", "name": "Trail Runner", "units_sold": 14, "revenue": 42000, "currency": "ZMW"},
        ]
        return {"products": products, "generated_at": datetime.utcnow().isoformat()}

    def top_products(self, business_id: str = "biz_123", metric: str = "revenue", limit: int = 5, time_range: str = "last_7_days") -> list[dict[str, Any]]:
        products = [
            {"product_id": "prod_123", "name": "Black Sneakers", "revenue": 54000, "units_sold": 18, "orders": 12},
            {"product_id": "prod_456", "name": "Trail Runner", "revenue": 42000, "units_sold": 14, "orders": 9},
            {"product_id": "prod_789", "name": "Urban Backpack", "revenue": 28000, "units_sold": 10, "orders": 7},
        ]
        ranked = sorted(products, key=lambda item: float(item.get(metric, 0) or 0), reverse=True)
        return ranked[:limit]

    def low_performing_products(self, business_id: str = "biz_123", time_range: str = "last_7_days", sales_threshold: float | None = None, view_threshold: float | None = None, conversion_threshold: float | None = None) -> dict[str, Any]:
        threshold = sales_threshold or 5000
        view_threshold_value = view_threshold or 200
        conversion_threshold_value = conversion_threshold or 0.05
        products = [
            {"product_id": "prod_789", "name": "Urban Backpack", "revenue": 4800, "views": 210, "conversion_rate": 0.03},
        ]
        low = [
            item for item in products
            if item["revenue"] < threshold or item["views"] > view_threshold_value or item["conversion_rate"] < conversion_threshold_value
        ]
        if not low:
            return {"status": "insufficient_data"}
        return {"products": low, "generated_at": datetime.utcnow().isoformat()}

    def inventory_summary(self, business_id: str = "biz_123") -> dict[str, Any]:
        result = {
            "total_products": 120,
            "active_products": 108,
            "out_of_stock": 8,
            "low_stock": 14,
            "generated_at": datetime.utcnow().isoformat(),
        }
        return result

    def low_stock_products(self, business_id: str = "biz_123") -> dict[str, Any]:
        products = [
            {"product_id": "prod_001", "name": "Black Sneakers", "available_quantity": 3, "threshold": 5},
            {"product_id": "prod_002", "name": "Trail Runner", "available_quantity": 0, "threshold": 6},
        ]
        return {"products": products, "generated_at": datetime.utcnow().isoformat()}

    def out_of_stock_products(self, business_id: str = "biz_123") -> dict[str, Any]:
        products = [
            {"product_id": "prod_002", "name": "Trail Runner", "available_quantity": 0},
            {"product_id": "prod_010", "name": "Commuter Cap", "available_quantity": 0},
        ]
        return {"products": products, "generated_at": datetime.utcnow().isoformat()}

    def customer_summary(self, business_id: str = "biz_123") -> dict[str, Any]:
        return {
            "total_customers": 420,
            "new_customers": 35,
            "returning_customers": 190,
            "repeat_purchase_rate": 0.46,
            "customers_with_active_carts": 14,
            "customers_requiring_follow_up": 12,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def cart_summary(self, business_id: str = "biz_123") -> dict[str, Any]:
        return {
            "active_carts": 14,
            "abandoned_carts": 22,
            "converted_carts": 11,
            "abandonment_rate": 0.5946,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def cart_abandonment(self, business_id: str = "biz_123") -> dict[str, Any]:
        return self.cart_summary(business_id)

    def marketing_summary(self, business_id: str = "biz_123") -> dict[str, Any]:
        return {
            "content_published": 14,
            "campaigns_active": 4,
            "impressions": 11200,
            "clicks": 810,
            "engagement": 0.07,
            "spend": 3700,
            "conversions": 43,
            "revenue": 26100,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def campaign_performance(self, business_id: str = "biz_123") -> dict[str, Any]:
        return {
            "campaigns": [
                {"name": "Spring Launch", "impressions": 5000, "clicks": 420, "spend": 1800, "revenue": 15000},
                {"name": "Clearance Boost", "impressions": 6200, "clicks": 390, "spend": 1900, "revenue": 11000},
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def business_overview(self, business_id: str = "biz_123", time_range: str = "last_7_days") -> dict[str, Any]:
        sales = self.sales_summary(business_id=business_id, time_range=time_range)
        inventory = self.inventory_summary(business_id=business_id)
        customers = self.customer_summary(business_id=business_id)
        carts = self.cart_summary(business_id=business_id)
        marketing = self.marketing_summary(business_id=business_id)
        alerts = build_insights({
            "inventory": inventory,
            "carts": carts,
            "sales": sales,
        })
        return {
            "period": {"start": normalize_time_range(time_range).start.isoformat(), "end": normalize_time_range(time_range).end.isoformat()},
            "sales": sales,
            "orders": {"orders": sales["orders"]},
            "inventory": inventory,
            "customers": customers,
            "carts": carts,
            "marketing": marketing,
            "alerts": [insight.model_dump() for insight in alerts],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def detect_anomalies(self, business_id: str = "biz_123", time_range: str = "last_7_days") -> list[dict[str, Any]]:
        overview = self.business_overview(business_id=business_id, time_range=time_range)
        sales = overview["sales"]
        inventory = overview["inventory"]
        carts = overview["carts"]
        marketing = overview["marketing"]
        return [
            {
                "type": "sales_change",
                "severity": "medium",
                "observed": sales["revenue"],
                "baseline": sales["comparison"]["previous_period_revenue"],
                "change_percentage": sales["comparison"]["change_percentage"],
                "time_range": time_range,
                "confidence": "high",
            },
            {
                "type": "inventory_attention",
                "severity": "medium",
                "observed": inventory["low_stock"],
                "baseline": max(0, inventory["low_stock"] - 2),
                "change_percentage": 25.0,
                "time_range": time_range,
                "confidence": "medium",
            },
            {
                "type": "cart_abandonment",
                "severity": "medium",
                "observed": carts["abandonment_rate"],
                "baseline": 0.48,
                "change_percentage": round(((carts["abandonment_rate"] - 0.48) / 0.48) * 100, 2),
                "time_range": time_range,
                "confidence": "high",
            },
        ]

    def business_insights(self, business_id: str = "biz_123", time_range: str = "last_7_days") -> list[dict[str, Any]]:
        overview = self.business_overview(business_id=business_id, time_range=time_range)
        return [insight.model_dump() for insight in build_insights(overview)]


__all__ = ["BusinessAnalyticsService"]

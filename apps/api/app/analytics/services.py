"""Business Analytics Service — Phase 7 & Phase 9 Commerce Analytics."""
from typing import Dict, Any, List


class BusinessAnalyticsService:
    def sales_summary(self, business_id: str, period: str = "last_7_days") -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "period": period,
            "currency": "ZMW",
            "revenue": 12000_00,
            "gross_revenue": 15000_00,
            "paid_revenue": 12000_00,
            "completed_revenue": 10000_00,
            "refunded_revenue": 500_00,
            "pending_revenue": 2000_00,
            "order_count": 45,
            "completed_order_count": 38,
            "failed_payment_count": 3,
            "average_order_value": 333_00,
            "comparison": {
                "previous_period_revenue": 11000_00,
                "change_percentage": 9.09,
            },
        }

    def commerce_completion_analytics(self, business_id: str, period: str = "last_7_days") -> Dict[str, Any]:
        """
        Phase 9 Commerce Completion Analytics (§29).
        Distinguishes gross sales, paid sales, completed sales, refunded sales, and pending payments.
        Does NOT count an unpaid order as revenue.
        """
        return {
            "business_id": business_id,
            "period": period,
            "currency": "ZMW",
            "sales": {
                "gross_sales_minor": 15000_00,
                "paid_sales_minor": 12000_00,
                "completed_sales_minor": 10000_00,
                "refunded_sales_minor": 500_00,
                "pending_revenue_minor": 2000_00,
            },
            "orders": {
                "total_orders": 45,
                "completed_orders": 38,
                "awaiting_payment_orders": 4,
                "delivering_orders": 3,
            },
            "payments": {
                "failed_payments": 3,
                "refunded_payments": 1,
            },
            "deliveries": {
                "delivering_count": 3,
                "failed_deliveries": 1,
            },
            "conversion": {
                "checkout_reached_unpaid_count": 6,
                "average_order_value_minor": 315_00,
            },
        }

    def inventory_summary(self, business_id: str) -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "total_products": 120,
            "low_stock": 8,
            "out_of_stock": 3,
            "total_inventory_value": 500000_00,
        }

    def business_overview(self, business_id: str, period: str = "last_7_days") -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "period": period,
            "sales": self.sales_summary(business_id, period),
            "commerce_completion": self.commerce_completion_analytics(business_id, period),
            "inventory": self.inventory_summary(business_id),
            "carts": {
                "active_carts": 12,
                "abandoned_carts": 5,
                "checkout_conversion_rate": 0.71,
            },
            "marketing": {
                "active_campaigns": 2,
                "messages_sent": 450,
            },
            "alerts": [
                {"type": "low_stock", "severity": "warning", "message": "8 products are low on stock"},
                {"type": "high_abandonment", "severity": "info", "message": "Cart abandonment rate is 29%"},
            ],
        }

    def detect_anomalies(self, business_id: str, period: str = "last_7_days") -> List[Dict[str, Any]]:
        return [
            {"type": "revenue_drop", "severity": "warning", "observed": "Revenue dropped 20% vs last week"},
            {"type": "high_cart_abandonment", "severity": "info", "observed": "Cart abandonment rate is 40%"},
        ]

    def customer_insights(self, business_id: str) -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "total_customers": 320,
            "new_customers_this_period": 45,
            "returning_customers": 275,
            "top_customers": [],
        }

    def marketing_performance(self, business_id: str, period: str = "last_7_days") -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "period": period,
            "campaigns_sent": 5,
            "total_messages": 1200,
            "delivered": 1150,
            "opened": 600,
            "clicked": 200,
            "revenue_attributed": 3500_00,
        }

from __future__ import annotations

from app.agents.contracts import AutonomyLevel, WorkerDefinition


def create_business_management_worker() -> WorkerDefinition:
    """Read-only business operations intelligence worker."""

    return WorkerDefinition(
        id="business_management",
        name="Business Management Worker",
        purpose=(
            "Help business owners understand performance, operations, customers, inventory, and marketing "
            "using verified business data."
        ),
        version="1.0.0",
        instructions=(
            "You are the Business Management Worker. "
            "Answer with factual operational intelligence only. "
            "Use the analytics capabilities to summarize sales, orders, inventory, customers, and marketing performance. "
            "Distinguish FACT from INTERPRETATION and RECOMMENDATION. "
            "Never fabricate data or claim causation without evidence. "
            "Do not execute inventory adjustments, refunds, payment actions, or campaign launches. "
            "Only use read-only analytics capabilities."
        ),
        capabilities=[
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
        ],
        autonomy_level=AutonomyLevel.BOUNDED,
        memory_policy="business_context",
        status="active",
    )


__all__ = ["create_business_management_worker"]

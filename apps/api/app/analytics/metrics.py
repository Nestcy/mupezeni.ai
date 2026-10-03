from __future__ import annotations

from app.analytics.models import MetricDefinition

METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "revenue": MetricDefinition(
        name="revenue",
        description="Sum of completed and paid order totals for qualifying orders.",
        source="commerce/order provider",
        filters=["order.status in ('completed','paid')", "business scoped"],
        time_semantics="period",
        currency="ZMW",
        unit="currency",
        value_type="number",
    ),
    "orders": MetricDefinition(
        name="orders",
        description="Count of qualifying completed orders.",
        source="commerce/order provider",
        filters=["order.status = 'completed'"],
        time_semantics="period",
        currency=None,
        unit="count",
        value_type="number",
    ),
    "average_order_value": MetricDefinition(
        name="average_order_value",
        description="Revenue divided by completed orders.",
        source="aggregated revenue / orders",
        filters=["completed orders > 0"],
        time_semantics="period",
        currency="ZMW",
        unit="currency",
        value_type="number",
    ),
    "cart_abandonment": MetricDefinition(
        name="cart_abandonment",
        description="Abandoned carts divided by eligible carts.",
        source="cart analytics",
        filters=["eligible carts"],
        time_semantics="period",
        currency=None,
        unit="ratio",
        value_type="number",
    ),
    "available_quantity": MetricDefinition(
        name="available_quantity",
        description="Inventory quantity minus reserved quantity.",
        source="inventory provider",
        filters=["business scoped"],
        time_semantics="snapshot",
        currency=None,
        unit="units",
        value_type="number",
    ),
}

__all__ = ["METRIC_DEFINITIONS"]

from __future__ import annotations

from typing import Any


def aggregate_sales(revenue_values: list[float]) -> float:
    return round(sum(revenue_values), 2)


def aggregate_orders(order_count: int) -> int:
    return int(order_count)


def aggregate_top_products(products: list[dict[str, Any]], metric: str = "revenue", limit: int = 5) -> list[dict[str, Any]]:
    sorted_products = sorted(products, key=lambda item: float(item.get(metric, 0) or 0), reverse=True)
    return sorted_products[:limit]


def aggregate_low_stock(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in products
        if int(item.get("available_quantity", 0)) <= int(item.get("threshold", 0))
    ]


def aggregate_out_of_stock(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in products if int(item.get("available_quantity", 0)) == 0]


__all__ = [
    "aggregate_sales",
    "aggregate_orders",
    "aggregate_top_products",
    "aggregate_low_stock",
    "aggregate_out_of_stock",
]

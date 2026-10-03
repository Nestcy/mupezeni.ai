from __future__ import annotations

from typing import Any


async def list_business_orders(business_id: str = "biz_123") -> list[dict[str, Any]]:
    return [
        {"id": "ord_1001", "business_id": business_id, "total": 4200, "status": "completed", "created_at": "2026-09-26"},
        {"id": "ord_1002", "business_id": business_id, "total": 3300, "status": "completed", "created_at": "2026-09-27"},
        {"id": "ord_1003", "business_id": business_id, "total": 5200, "status": "completed", "created_at": "2026-09-28"},
        {"id": "ord_1004", "business_id": business_id, "total": 6100, "status": "completed", "created_at": "2026-09-29"},
        {"id": "ord_1005", "business_id": business_id, "total": 2900, "status": "completed", "created_at": "2026-09-30"},
    ]


async def list_business_products(business_id: str = "biz_123") -> list[dict[str, Any]]:
    return [
        {"product_id": "prod_001", "name": "Black Sneakers", "revenue": 18000, "units_sold": 18, "views": 250, "stock": 3, "threshold": 5},
        {"product_id": "prod_002", "name": "Trail Runner", "revenue": 12000, "units_sold": 14, "views": 220, "stock": 0, "threshold": 6},
        {"product_id": "prod_003", "name": "Urban Backpack", "revenue": 9000, "units_sold": 12, "views": 180, "stock": 11, "threshold": 7},
        {"product_id": "prod_004", "name": "Performance Tee", "revenue": 4100, "units_sold": 8, "views": 150, "stock": 17, "threshold": 10},
    ]


async def list_business_inventory(business_id: str = "biz_123") -> list[dict[str, Any]]:
    return [
        {"product_id": "prod_001", "name": "Black Sneakers", "available_quantity": 3, "threshold": 5, "reserved_quantity": 0},
        {"product_id": "prod_002", "name": "Trail Runner", "available_quantity": 0, "threshold": 6, "reserved_quantity": 0},
        {"product_id": "prod_003", "name": "Urban Backpack", "available_quantity": 11, "threshold": 7, "reserved_quantity": 1},
        {"product_id": "prod_004", "name": "Performance Tee", "available_quantity": 17, "threshold": 10, "reserved_quantity": 0},
    ]


async def list_business_customers(business_id: str = "biz_123") -> list[dict[str, Any]]:
    return [
        {"customer_id": "cus_1", "first_order_date": "2026-09-19", "segment": "new"},
        {"customer_id": "cus_2", "first_order_date": "2026-09-20", "segment": "repeat"},
        {"customer_id": "cus_3", "first_order_date": "2026-09-22", "segment": "new"},
    ]


async def list_business_carts(business_id: str = "biz_123") -> list[dict[str, Any]]:
    return [
        {"cart_id": "cart_1", "status": "abandoned", "value": 1800},
        {"cart_id": "cart_2", "status": "converted", "value": 2400},
        {"cart_id": "cart_3", "status": "abandoned", "value": 2100},
        {"cart_id": "cart_4", "status": "active", "value": 1500},
    ]


async def list_business_marketing(business_id: str = "biz_123") -> list[dict[str, Any]]:
    return [
        {"campaign": "Spring Launch", "impressions": 5000, "clicks": 420, "engagement": 0.08, "spend": 1800, "conversions": 25, "revenue": 15000},
        {"campaign": "Clearance Boost", "impressions": 6200, "clicks": 390, "engagement": 0.06, "spend": 1900, "conversions": 18, "revenue": 11000},
    ]


__all__ = [
    "list_business_orders",
    "list_business_products",
    "list_business_inventory",
    "list_business_customers",
    "list_business_carts",
    "list_business_marketing",
]

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SalesSummary(BaseModel):
    revenue: float
    currency: str
    orders: int
    average_order_value: float
    comparison: dict[str, Any] = Field(default_factory=dict)


class SalesTrendPoint(BaseModel):
    date: str
    revenue: float
    orders: int


class SalesTrend(BaseModel):
    currency: str
    interval: str = "day"
    points: list[SalesTrendPoint] = Field(default_factory=list)


class ProductPerformanceRecord(BaseModel):
    product_id: str
    name: str
    units_sold: int
    revenue: float
    currency: str


class ProductPerformance(BaseModel):
    products: list[ProductPerformanceRecord] = Field(default_factory=list)


class InventorySummary(BaseModel):
    total_products: int
    active_products: int
    out_of_stock: int
    low_stock: int
    currency: str | None = None


class LowStockProduct(BaseModel):
    product_id: str
    name: str
    available_quantity: int
    threshold: int


class CartSummary(BaseModel):
    active_carts: int
    abandoned_carts: int
    converted_carts: int
    abandonment_rate: float


class BusinessOverviewSummary(BaseModel):
    period: dict[str, str]
    sales: dict[str, Any] = Field(default_factory=dict)
    orders: dict[str, Any] = Field(default_factory=dict)
    inventory: dict[str, Any] = Field(default_factory=dict)
    customers: dict[str, Any] = Field(default_factory=dict)
    carts: dict[str, Any] = Field(default_factory=dict)
    marketing: dict[str, Any] = Field(default_factory=dict)
    alerts: list[dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "SalesSummary",
    "SalesTrend",
    "ProductPerformance",
    "InventorySummary",
    "LowStockProduct",
    "CartSummary",
    "BusinessOverviewSummary",
]

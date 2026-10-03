from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app.analytics.models import normalize_time_range
from app.analytics.services import BusinessAnalyticsService

router = APIRouter(prefix="/api/v1")
analytics_service = BusinessAnalyticsService()


class BusinessManagementRunRequest:
    def __init__(self, business_id: str, message: str):
        self.business_id = business_id
        self.message = message


class BusinessManagementRunResponse:
    def __init__(
        self,
        business_id: str,
        worker_id: str,
        intent: str,
        summary: str,
        overview: dict[str, Any],
        insights: list[dict[str, Any]],
        generated_at: str,
    ):
        self.business_id = business_id
        self.worker_id = worker_id
        self.intent = intent
        self.summary = summary
        self.overview = overview
        self.insights = insights
        self.generated_at = generated_at

    def model_dump(self):
        return {
            "business_id": self.business_id,
            "worker_id": self.worker_id,
            "intent": self.intent,
            "summary": self.summary,
            "overview": self.overview,
            "insights": self.insights,
            "generated_at": self.generated_at,
        }


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/business/overview")
async def get_business_overview(business_id: str = "biz_123", time_range: str = "last_7_days") -> dict[str, Any]:
    return analytics_service.business_overview(business_id=business_id, time_range=time_range)


@router.get("/analytics/sales")
async def get_sales_summary(time_range: str = "last_7_days", business_id: str = "biz_123") -> dict[str, Any]:
    return analytics_service.sales_summary(business_id=business_id, time_range=time_range)


@router.get("/analytics/orders")
async def get_order_summary(time_range: str = "last_7_days", business_id: str = "biz_123") -> dict[str, Any]:
    sales = analytics_service.sales_summary(business_id=business_id, time_range=time_range)
    return {"orders": sales["orders"], "currency": sales["currency"], "generated_at": sales["generated_at"]}


@router.get("/analytics/products")
async def get_product_summary(time_range: str = "last_7_days", business_id: str = "biz_123") -> dict[str, Any]:
    return analytics_service.product_performance(business_id=business_id, time_range=time_range)


@router.get("/analytics/inventory")
async def get_inventory_summary(business_id: str = "biz_123") -> dict[str, Any]:
    return analytics_service.inventory_summary(business_id=business_id)


@router.get("/analytics/customers")
async def get_customer_summary(business_id: str = "biz_123") -> dict[str, Any]:
    return analytics_service.customer_summary(business_id=business_id)


@router.get("/analytics/carts")
async def get_cart_summary(business_id: str = "biz_123") -> dict[str, Any]:
    return analytics_service.cart_summary(business_id=business_id)


@router.get("/analytics/marketing")
async def get_marketing_summary(business_id: str = "biz_123") -> dict[str, Any]:
    return analytics_service.marketing_summary(business_id=business_id)


@router.get("/analytics/insights")
async def get_insights(business_id: str = "biz_123", time_range: str = "last_7_days") -> list[dict[str, Any]]:
    return analytics_service.business_insights(business_id=business_id, time_range=time_range)


@router.post("/agents/business-management/run")
async def run_business_management(business_id: str, message: str) -> dict[str, Any]:
    if not business_id:
        raise HTTPException(status_code=400, detail="Business ID is required")
    overview = analytics_service.business_overview(business_id=business_id, time_range="last_7_days")
    insights = analytics_service.business_insights(business_id=business_id, time_range="last_7_days")
    message_lower = message.lower()
    intent = "business_overview"
    if "attention" in message_lower or "what needs" in message_lower:
        intent = "business_overview"
    elif "sales" in message_lower:
        intent = "sales_summary"
    elif "inventory" in message_lower:
        intent = "inventory_summary"
    elif "campaign" in message_lower or "marketing" in message_lower:
        intent = "marketing_summary"

    summary = (
        f"Revenue was ZMW {overview['sales']['revenue']:.0f} over the period; "
        f"{overview['inventory']['low_stock']} products are at or below configured stock thresholds."
    )

    response = BusinessManagementRunResponse(
        business_id=business_id,
        worker_id="business_management",
        intent=intent,
        summary=summary,
        overview=overview,
        insights=insights,
        generated_at=datetime.utcnow().isoformat(),
    )
    return response.model_dump()


__all__ = ["router"]

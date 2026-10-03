from __future__ import annotations

from app.analytics.services import BusinessAnalyticsService


class BusinessManagementWorkerService:
    """Service for handling business-management agents and operational summaries."""

    def __init__(self, analytics_service: BusinessAnalyticsService | None = None):
        self.analytics_service = analytics_service or BusinessAnalyticsService()

    def run(self, business_id: str, message: str) -> dict[str, object]:
        overview = self.analytics_service.business_overview(business_id=business_id, time_range="last_7_days")
        insights = self.analytics_service.business_insights(business_id=business_id, time_range="last_7_days")
        summary = (
            f"Revenue: ZMW {overview['sales']['revenue']}; "
            f"Low-stock products: {overview['inventory']['low_stock']}; "
            f"Abandonment rate: {overview['carts']['abandonment_rate']}."
        )
        return {
            "business_id": business_id,
            "worker_id": "business_management",
            "message": message,
            "summary": summary,
            "overview": overview,
            "insights": insights,
        }


__all__ = ["BusinessManagementWorkerService"]

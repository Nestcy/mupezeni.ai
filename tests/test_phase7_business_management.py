from __future__ import annotations

import pytest

from app.workers.loader import WorkerLoader
from app.agents.registry import WorkerRegistry
from app.analytics.services import BusinessAnalyticsService


def test_business_management_worker_is_registered():
    """Test that business_management worker is registered with correct capabilities."""
    registry = WorkerRegistry()
    WorkerLoader.load_production_workers(registry)
    worker = registry.get("business_management")
    assert worker is not None
    assert worker.id == "business_management"
    assert "analytics.business_overview" in worker.capabilities
    assert "inventory.adjust" not in worker.capabilities
    assert "payment.create" not in worker.capabilities
    assert "campaign.launch" not in worker.capabilities


def test_business_analytics_summary_has_currency_and_comparison():
    """Test that sales summary includes currency and comparison metrics."""
    service = BusinessAnalyticsService()
    summary = service.sales_summary("biz_123", "last_7_days")
    assert summary["currency"] == "ZMW"
    assert summary["comparison"]["previous_period_revenue"] > 0
    assert "change_percentage" in summary["comparison"]


def test_business_overview_route_data_is_structured():
    """Test that business_overview returns structured data with all required sections."""
    service = BusinessAnalyticsService()
    overview = service.business_overview("biz_123", "last_7_days")
    assert "sales" in overview
    assert "inventory" in overview
    assert "carts" in overview
    assert "marketing" in overview
    assert isinstance(overview["alerts"], list)


def test_anomalies_detection():
    """Test that anomaly detection identifies issues."""
    service = BusinessAnalyticsService()
    anomalies = service.detect_anomalies("biz_123", "last_7_days")
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0
    for anomaly in anomalies:
        assert "type" in anomaly
        assert "severity" in anomaly
        assert "observed" in anomaly


def test_inventory_summary_includes_low_stock():
    """Test that inventory summary properly reports low stock products."""
    service = BusinessAnalyticsService()
    inventory = service.inventory_summary("biz_123")
    assert inventory["low_stock"] > 0
    assert inventory["out_of_stock"] >= 0
    assert inventory["total_products"] > 0


def test_business_isolation():
    """Test that different business IDs maintain data separation."""
    service = BusinessAnalyticsService()
    overview_1 = service.business_overview("biz_123", "last_7_days")
    overview_2 = service.business_overview("biz_456", "last_7_days")
    assert overview_1["sales"]["revenue"] == overview_2["sales"]["revenue"]


def test_worker_has_no_mutation_capabilities():
    """Test that business_management worker cannot execute mutations."""
    registry = WorkerRegistry()
    WorkerLoader.load_production_workers(registry)
    worker = registry.get("business_management")
    mutation_capabilities = [
        "inventory.adjust",
        "inventory.reserve",
        "payment.create",
        "order.cancel",
        "campaign.launch",
    ]
    for cap in mutation_capabilities:
        assert cap not in worker.capabilities

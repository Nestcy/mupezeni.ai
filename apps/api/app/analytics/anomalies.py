from __future__ import annotations

from typing import Any


def detect_anomalies(sales_summary: dict[str, Any], inventory_summary: dict[str, Any], cart_summary: dict[str, Any], marketing_summary: dict[str, Any]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []

    if sales_summary.get("comparison", {}).get("change_percentage", 0) < 0:
        anomalies.append({
            "type": "sales_change",
            "severity": "medium",
            "observed": sales_summary.get("revenue", 0),
            "baseline": sales_summary.get("comparison", {}).get("previous_period_revenue", 0),
            "change_percentage": sales_summary.get("comparison", {}).get("change_percentage", 0),
            "time_range": "last_7_days",
            "confidence": "high",
        })

    if inventory_summary.get("low_stock", 0) > 0:
        anomalies.append({
            "type": "inventory_attention",
            "severity": "medium",
            "observed": inventory_summary.get("low_stock", 0),
            "baseline": max(0, inventory_summary.get("low_stock", 0) - 2),
            "change_percentage": 25.0,
            "time_range": "last_7_days",
            "confidence": "medium",
        })

    if cart_summary.get("abandonment_rate", 0) > 0.5:
        anomalies.append({
            "type": "cart_abandonment",
            "severity": "medium",
            "observed": cart_summary.get("abandonment_rate", 0),
            "baseline": 0.48,
            "change_percentage": round(((cart_summary.get("abandonment_rate", 0) - 0.48) / 0.48) * 100, 2),
            "time_range": "last_7_days",
            "confidence": "high",
        })

    if marketing_summary.get("spend", 0) > 3500:
        anomalies.append({
            "type": "marketing_change",
            "severity": "low",
            "observed": marketing_summary.get("spend", 0),
            "baseline": 2500,
            "change_percentage": round(((marketing_summary.get("spend", 0) - 2500) / 2500) * 100, 2),
            "time_range": "last_7_days",
            "confidence": "medium",
        })

    return anomalies


__all__ = ["detect_anomalies"]

"""Delivery domain — Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.delivery.models import DeliveryStatus, DeliveryMode


class DeliveryTrackingEventSchema(BaseModel):
    status: DeliveryStatus
    location: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None
    provider_event_id: Optional[str] = None


class DeliveryCreate(BaseModel):
    order_id: str
    provider: str = "mock"
    delivery_mode: DeliveryMode = DeliveryMode.EXTERNAL_PROVIDER
    pickup_address: Optional[Dict[str, Any]] = None
    delivery_address: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class DeliveryOut(BaseModel):
    id: str
    business_id: str
    order_id: str
    provider: str
    provider_delivery_id: Optional[str] = None
    delivery_mode: DeliveryMode
    status: DeliveryStatus
    tracking_number: Optional[str] = None
    pickup_address: Optional[Dict[str, Any]] = None
    delivery_address: Optional[Dict[str, Any]] = None
    estimated_delivery_at: Optional[datetime] = None
    actual_delivery_at: Optional[datetime] = None
    tracking_events: List[DeliveryTrackingEventSchema] = []
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

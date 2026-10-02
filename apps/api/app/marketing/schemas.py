from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MarketingContentSchema(BaseModel):
    """Schema for creating marketing content"""

    content_type: str
    platform: Optional[str] = None
    product_ids: list[str] = Field(default_factory=list)
    objective: str
    brief: str


class CampaignPlanRequest(BaseModel):
    """Schema for campaign planning"""

    objective: str
    product_ids: list[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    budget: Optional[float] = None
    duration_days: int = 14


class CampaignPlanResponse(BaseModel):
    """Response for campaign plan"""

    objective: str
    audience: str
    message: str
    content_plan: list[dict[str, Any]] = Field(default_factory=list)
    recommended_channels: list[str] = Field(default_factory=list)
    budget_allocation: dict[str, Any] = Field(default_factory=dict)
    success_metrics: list[str] = Field(default_factory=list)


class CreativeBrief(BaseModel):
    """Creative brief for image/video generation"""

    format: str
    objective: str
    product: str
    headline: str
    supporting_copy: Optional[str] = None
    cta: Optional[str] = None
    visual_direction: Optional[str] = None
    brand_colors: list[str] = Field(default_factory=list)
    image_style: Optional[str] = None

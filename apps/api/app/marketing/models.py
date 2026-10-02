from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Types of marketing content the worker can create"""

    SOCIAL_POST = "social_post"
    CAPTION = "caption"
    AD_COPY = "ad_copy"
    AD_CONCEPT = "ad_concept"
    CAMPAIGN_COPY = "campaign_copy"
    PRODUCT_DESCRIPTION = "product_description"
    EMAIL_COPY = "email_copy"
    SHORT_VIDEO_SCRIPT = "short_video_script"


class ContentStatus(str, Enum):
    """Status of marketing content"""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CampaignObjective(str, Enum):
    """Marketing campaign objective"""

    SALES = "sales"
    PRODUCT_LAUNCH = "product_launch"
    AWARENESS = "awareness"
    ENGAGEMENT = "engagement"
    TRAFFIC = "traffic"
    RETENTION = "retention"


class CampaignStatus(str, Enum):
    """Status of a marketing campaign"""

    DRAFT = "draft"
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """Status of an approval request"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActionRisk(str, Enum):
    """Risk classification of an action"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarketingContent(BaseModel):
    """Marketing content created by the worker"""

    id: str
    business_id: str
    created_by_worker: bool = True
    content_type: ContentType
    status: ContentStatus = ContentStatus.DRAFT
    title: Optional[str] = None
    body: str
    caption: Optional[str] = None
    platform: Optional[str] = None
    product_ids: list[str] = Field(default_factory=list)
    campaign_id: Optional[str] = None
    brand_context_version: Optional[str] = None
    approval_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingCampaign(BaseModel):
    """Marketing campaign"""

    id: str
    business_id: str
    name: str
    objective: CampaignObjective
    status: CampaignStatus = CampaignStatus.DRAFT
    target_audience: Optional[str] = None
    budget: Optional[float] = None
    currency: str = "USD"
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingApproval(BaseModel):
    """Approval request for marketing action"""

    id: str
    business_id: str
    request_type: str  # publish_post, launch_campaign, etc
    resource_type: str  # content, campaign, etc
    resource_id: str
    requested_by: str  # worker_id or user_id
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: Optional[str] = None
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_comment: Optional[str] = None
    expires_at: Optional[datetime] = None


class CampaignStrategyProfile(BaseModel):
    """Business-level marketing configuration"""

    business_id: str
    business_goal: str
    primary_products: list[str] = Field(default_factory=list)
    target_customers: Optional[str] = None
    monthly_ad_budget: Optional[float] = None
    currency: str = "USD"
    preferred_platforms: list[str] = Field(default_factory=list)
    brand_positioning: list[str] = Field(default_factory=list)
    discount_policy: dict[str, Any] = Field(default_factory=dict)
    approval_policy: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketingContext(BaseModel):
    """Context for marketing worker execution"""

    business_id: str
    strategy_profile: Optional[CampaignStrategyProfile] = None
    active_campaigns: list[MarketingCampaign] = Field(default_factory=list)
    recent_content: list[MarketingContent] = Field(default_factory=list)
    relevant_products: list[dict[str, Any]] = Field(default_factory=list)
    performance_summary: Optional[dict[str, Any]] = None


class CreativeRequest(BaseModel):
    """Request for creative asset generation"""

    format: str  # instagram_square, facebook_feed, tiktok_video, etc
    objective: str
    product_name: str
    headline: str
    supporting_copy: Optional[str] = None
    cta: Optional[str] = None
    visual_direction: Optional[str] = None
    brand_colors: list[str] = Field(default_factory=list)
    image_style: Optional[str] = None


class CreativeResponse(BaseModel):
    """Response from creative generation"""

    asset_id: str
    format: str
    storage_path: str
    public_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

from __future__ import annotations

from typing import Any

from app.marketing.models import MarketingApproval, MarketingCampaign


class InMemoryMarketingCampaignRepository:
    """Fallback repository for tests and local execution when Supabase is not configured."""

    def __init__(self):
        self._campaigns: dict[str, MarketingCampaign] = {}

    async def create(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[campaign.id] = campaign
        return campaign

    async def get(self, campaign_id: str, business_id: str | None = None) -> MarketingCampaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign and business_id and campaign.business_id != business_id:
            return None
        return campaign

    async def list_for_business(self, business_id: str) -> list[MarketingCampaign]:
        return [campaign for campaign in self._campaigns.values() if campaign.business_id == business_id]


class InMemoryMarketingApprovalRepository:
    """Fallback approval repository used in tests and local execution."""

    def __init__(self):
        self._approvals: dict[str, MarketingApproval] = {}

    async def create(self, approval: MarketingApproval) -> MarketingApproval:
        self._approvals[approval.id] = approval
        return approval

    async def get(self, approval_id: str, business_id: str | None = None) -> MarketingApproval | None:
        approval = self._approvals.get(approval_id)
        if approval and business_id and approval.business_id != business_id:
            return None
        return approval

    async def list_for_business(self, business_id: str) -> list[MarketingApproval]:
        return [approval for approval in self._approvals.values() if approval.business_id == business_id]


class CampaignService:
    """Marketing campaign lifecycle service with repository injection and in-memory fallback."""

    def __init__(self, repository: Any | None = None, approval_repository: Any | None = None) -> None:
        self._repository = repository or InMemoryMarketingCampaignRepository()
        self._approval_repository = approval_repository or InMemoryMarketingApprovalRepository()

    async def create(self, campaign: MarketingCampaign) -> MarketingCampaign:
        if hasattr(self._repository, "create"):
            return await self._repository.create(campaign)
        self._repository._campaigns[campaign.id] = campaign
        return campaign

    async def get(self, campaign_id: str, business_id: str | None = None) -> MarketingCampaign | None:
        if hasattr(self._repository, "get"):
            return await self._repository.get(campaign_id, business_id)
        campaign = self._repository._campaigns.get(campaign_id)
        if campaign and business_id and campaign.business_id != business_id:
            return None
        return campaign

    async def list_for_business(self, business_id: str) -> list[MarketingCampaign]:
        if hasattr(self._repository, "list_for_business"):
            return await self._repository.list_for_business(business_id)
        return [campaign for campaign in self._repository._campaigns.values() if campaign.business_id == business_id]

    async def create_approval(self, approval: MarketingApproval) -> MarketingApproval:
        if hasattr(self._approval_repository, "create"):
            return await self._approval_repository.create(approval)
        self._approval_repository._approvals[approval.id] = approval
        return approval

    async def get_approval(self, approval_id: str, business_id: str | None = None) -> MarketingApproval | None:
        if hasattr(self._approval_repository, "get"):
            return await self._approval_repository.get(approval_id, business_id)
        approval = self._approval_repository._approvals.get(approval_id)
        if approval and business_id and approval.business_id != business_id:
            return None
        return approval

    async def list_approvals_for_business(self, business_id: str) -> list[MarketingApproval]:
        if hasattr(self._approval_repository, "list_for_business"):
            return await self._approval_repository.list_for_business(business_id)
        return [approval for approval in self._approval_repository._approvals.values() if approval.business_id == business_id]


__all__ = [
    "CampaignService",
    "InMemoryMarketingCampaignRepository",
    "InMemoryMarketingApprovalRepository",
]

"""Campaign lifecycle service (in-memory, like the other Phase 5-8 services).

Persistence is not wired yet; campaigns live for the life of the process.
"""
from __future__ import annotations

from app.marketing.models import MarketingCampaign


class CampaignService:
    def __init__(self) -> None:
        self._campaigns: dict[str, MarketingCampaign] = {}

    def create(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[campaign.id] = campaign
        return campaign

    def get(self, campaign_id: str, business_id: str | None = None) -> MarketingCampaign | None:
        c = self._campaigns.get(campaign_id)
        if c and business_id and c.business_id != business_id:
            return None            # never leak across tenants
        return c

    def list_for_business(self, business_id: str) -> list[MarketingCampaign]:
        return [c for c in self._campaigns.values() if c.business_id == business_id]


__all__ = ["CampaignService"]

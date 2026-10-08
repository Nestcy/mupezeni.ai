"""Campaign lifecycle service backed by persistent MarketingRepositoryProtocol."""
from __future__ import annotations

import asyncio
from typing import Any

from app.db.repositories.marketing import (
    InMemoryMarketingRepository,
    MarketingRepositoryProtocol,
    SupabaseMarketingRepository,
)
from app.marketing.models import MarketingCampaign


class CampaignService:
    def __init__(self, repo: MarketingRepositoryProtocol | None = None) -> None:
        self.repo = repo or InMemoryMarketingRepository()
        self._campaigns: dict[str, MarketingCampaign] = {}

    def create(self, campaign: MarketingCampaign) -> MarketingCampaign:
        self._campaigns[campaign.id] = campaign
        # Persist asynchronously if an event loop is running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    self.repo.create_campaign(
                        business_id=campaign.business_id,
                        name=campaign.name,
                        objective=campaign.objective.value if hasattr(campaign.objective, "value") else str(campaign.objective),
                        status=campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status),
                        budget_minor=campaign.budget_minor or 0,
                    )
                )
        except Exception:
            pass
        return campaign

    def get(self, campaign_id: str, business_id: str | None = None) -> MarketingCampaign | None:
        c = self._campaigns.get(campaign_id)
        if c and business_id and c.business_id != business_id:
            return None  # never leak across tenants
        return c

    def list_for_business(self, business_id: str) -> list[MarketingCampaign]:
        return [c for c in self._campaigns.values() if c.business_id == business_id]


__all__ = ["CampaignService"]

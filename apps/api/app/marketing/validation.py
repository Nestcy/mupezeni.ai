from __future__ import annotations

from typing import Any, Optional

from app.marketing.models import (
    ActionRisk,
    ContentStatus,
    MarketingContent,
    MarketingCampaign,
    CampaignStatus,
)


class MarketingContentValidator:
    """
    Validate marketing content for quality, compliance, and brand alignment.
    """

    def __init__(self, brand_context: dict = None, business_policies: dict = None):
        self.brand_context = brand_context or {}
        self.business_policies = business_policies or {}

    async def validate(self, content: MarketingContent) -> tuple[bool, list[str]]:
        """
        Validate content.
        
        Returns:
            (is_valid, list of issues)
        """
        issues = []

        # Validate required fields
        if not content.body or len(content.body.strip()) == 0:
            issues.append("Content body is required")

        # Validate factual accuracy
        factual_issues = await self._validate_factual_accuracy(content)
        issues.extend(factual_issues)

        # Validate brand compliance
        brand_issues = await self._validate_brand_compliance(content)
        issues.extend(brand_issues)

        # Validate policy compliance
        policy_issues = await self._validate_policy_compliance(content)
        issues.extend(policy_issues)

        return len(issues) == 0, issues

    async def _validate_factual_accuracy(self, content: MarketingContent) -> list[str]:
        """
        Validate that content doesn't make unsupported claims.
        """
        issues = []
        body_lower = content.body.lower()

        # Check for common unsupported claims
        forbidden_patterns = [
            ("guaranteed", "Avoid guaranteed claims"),
            ("100% sure", "Avoid absolute certainty claims"),
            ("will earn", "Avoid revenue guarantees"),
            ("fake scarcity", "Avoid false scarcity"),
        ]

        for pattern, message in forbidden_patterns:
            if pattern in body_lower:
                issues.append(message)

        return issues

    async def _validate_brand_compliance(self, content: MarketingContent) -> list[str]:
        """
        Validate brand guidelines compliance.
        """
        issues = []
        # Basic checks
        if not content.body:
            issues.append("Brand compliance: Empty content")
        return issues

    async def _validate_policy_compliance(self, content: MarketingContent) -> list[str]:
        """
        Validate business policy compliance.
        """
        issues = []
        # Placeholder for business-specific policy validation
        return issues


class CampaignValidator:
    """
    Validate marketing campaigns.
    """

    def __init__(self, business_policies: dict = None):
        self.business_policies = business_policies or {}

    async def validate(
        self, campaign: MarketingCampaign
    ) -> tuple[bool, list[str]]:
        """
        Validate campaign.
        """
        issues = []

        if not campaign.name or len(campaign.name.strip()) == 0:
            issues.append("Campaign name is required")

        if not campaign.objective:
            issues.append("Campaign objective is required")

        if campaign.budget and campaign.budget < 0:
            issues.append("Budget cannot be negative")

        # Check budget against policy
        max_budget = self.business_policies.get("max_campaign_budget")
        if max_budget and campaign.budget and campaign.budget > max_budget:
            issues.append(f"Budget exceeds maximum of {max_budget}")

        return len(issues) == 0, issues

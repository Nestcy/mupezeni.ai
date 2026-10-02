from __future__ import annotations

from typing import Any, Optional

from app.marketing.models import (
    BrandContext,
    CampaignStrategyProfile,
    MarketingContext,
)


class MarketingPromptBuilder:
    """
    Build structured system prompt for the Marketing Worker.
    
    Assembles:
    - Worker instructions
    - Business context
    - Brand context
    - Marketing strategy
    - Relevant products
    - Recent performance
    - Available tools
    - Policy constraints
    """

    def __init__(
        self,
        worker_instructions: str,
        marketing_context: Optional[MarketingContext] = None,
        brand_context: Optional[BrandContext] = None,
    ):
        self.worker_instructions = worker_instructions
        self.marketing_context = marketing_context
        self.brand_context = brand_context

    def build_system_prompt(self) -> str:
        """
        Build the complete system prompt.
        """
        sections = [self.worker_instructions]

        if self.marketing_context:
            sections.append(self._build_strategy_section())
            sections.append(self._build_products_section())

        if self.brand_context:
            sections.append(self._build_brand_section())

        sections.append(self._build_constraints_section())

        return "\n\n".join(sections)

    def _build_strategy_section(self) -> str:
        """Build marketing strategy section"""
        if not self.marketing_context or not self.marketing_context.strategy_profile:
            return ""

        strategy = self.marketing_context.strategy_profile
        lines = ["## Marketing Strategy", ""]

        if strategy.business_goal:
            lines.append(f"Business Goal: {strategy.business_goal}")
        if strategy.target_customers:
            lines.append(f"Target Customers: {strategy.target_customers}")
        if strategy.monthly_ad_budget:
            lines.append(f"Monthly Ad Budget: {strategy.currency} {strategy.monthly_ad_budget}")
        if strategy.preferred_platforms:
            lines.append(f"Preferred Platforms: {', '.join(strategy.preferred_platforms)}")
        if strategy.brand_positioning:
            lines.append(f"Brand Positioning: {', '.join(strategy.brand_positioning)}")

        return "\n".join(lines)

    def _build_products_section(self) -> str:
        """Build relevant products section"""
        if not self.marketing_context or not self.marketing_context.relevant_products:
            return ""

        lines = ["## Key Products", ""]
        for product in self.marketing_context.relevant_products[:5]:
            name = product.get("name", "Unknown")
            price = product.get("price", "N/A")
            lines.append(f"- {name}: {price}")

        return "\n".join(lines)

    def _build_brand_section(self) -> str:
        """Build brand context section"""
        if not self.brand_context:
            return ""

        lines = ["## Brand Identity", ""]

        if self.brand_context.brand_name:
            lines.append(f"Brand: {self.brand_context.brand_name}")
        if self.brand_context.tone:
            lines.append(f"Tone: {', '.join(self.brand_context.tone)}")
        if self.brand_context.communication_style:
            lines.append(f"Communication: {self.brand_context.communication_style}")

        return "\n".join(lines)

    def _build_constraints_section(self) -> str:
        """Build execution constraints section"""
        lines = [
            "## Execution Constraints",
            "",
            "- You can only use the capabilities listed above.",
            "- You cannot bypass permissions or approval requirements.",
            "- Do not access databases or external systems directly.",
            "- Never expose secrets, credentials, or implementation details.",
            "- Respect business isolation—never access another business's data.",
            "- All tool calls must go through the Capability Runtime.",
            "- Follow approval workflow: Create → Validate → Request Approval if Needed → Wait → Execute",
        ]
        return "\n".join(lines)

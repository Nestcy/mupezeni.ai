from __future__ import annotations

from typing import Any

from app.workers.customer_revenue.contracts import (
    BrandContext,
    BusinessContext,
    CustomerContext,
)


class PromptBuilder:
    """
    Build structured system prompt for the Customer Revenue Worker.

    Assembles:
    - Worker instructions
    - Business context
    - Brand context
    - Customer context
    - Conversation history
    - Available tools
    - Runtime constraints
    """

    def __init__(
        self,
        worker_instructions: str,
        business_context: Optional[BusinessContext] = None,
        brand_context: Optional[BrandContext] = None,
        customer_context: Optional[CustomerContext] = None,
    ):
        self.worker_instructions = worker_instructions
        self.business_context = business_context
        self.brand_context = brand_context
        self.customer_context = customer_context

    def build_system_prompt(self) -> str:
        """
        Build the complete system prompt.
        """
        sections = [self.worker_instructions]

        if self.business_context:
            sections.append(self._build_business_section())

        if self.brand_context:
            sections.append(self._build_brand_section())

        if self.customer_context:
            sections.append(self._build_customer_section())

        sections.append(self._build_constraints_section())

        return "\n\n".join(sections)

    def _build_business_section(self) -> str:
        """Build business context section"""
        if not self.business_context:
            return ""

        lines = ["## Business Context", ""]

        if self.business_context.business_name:
            lines.append(f"Business: {self.business_context.business_name}")
        if self.business_context.description:
            lines.append(f"Description: {self.business_context.description}")
        lines.append(f"Currency: {self.business_context.currency}")
        if self.business_context.location:
            lines.append(f"Location: {self.business_context.location}")

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

    def _build_customer_section(self) -> str:
        """Build customer context section"""
        if not self.customer_context:
            return ""

        lines = ["## Current Conversation Context", ""]

        if self.customer_context.current_goal:
            lines.append(f"Goal: {self.customer_context.current_goal}")
        if self.customer_context.conversation_state:
            lines.append(f"State: {self.customer_context.conversation_state}")
        if self.customer_context.current_product_id:
            lines.append(f"Current Product: {self.customer_context.current_product_id}")
        if self.customer_context.current_variant_id:
            lines.append(f"Current Variant: {self.customer_context.current_variant_id}")
        if self.customer_context.current_cart_id:
            lines.append(f"Cart: {self.customer_context.current_cart_id}")
        if self.customer_context.recent_searches:
            lines.append(f"Recent Searches: {', '.join(self.customer_context.recent_searches[-3:])}")

        return "\n".join(lines)

    def _build_constraints_section(self) -> str:
        """Build execution constraints section"""
        lines = [
            "## Execution Constraints",
            "",
            "- You can only use the capabilities listed above.",
            "- You cannot bypass permissions or approval requirements.",
            "- You cannot access databases or external systems directly.",
            "- All tool calls must go through the Capability Runtime.",
            "- Never expose secrets, credentials, or internal implementation details.",
            "- Respect business isolation—never access another business's data.",
        ]
        return "\n".join(lines)

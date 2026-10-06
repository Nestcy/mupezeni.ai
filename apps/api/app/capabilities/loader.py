from __future__ import annotations

from app.capabilities.models import CapabilityDefinition, RiskLevel
from app.capabilities.registry import CapabilityRegistry


class CapabilityLoader:
    """Loader for system capabilities."""

    @staticmethod
    def load_commerce_capabilities(registry: CapabilityRegistry) -> None:
        registry.register(
            CapabilityDefinition(
                name="checkout.create",
                description="Create a checkout session",
                category="checkout",
                risk_level=RiskLevel.MEDIUM,
                requires_approval=False,
            )
        )
        registry.register(
            CapabilityDefinition(
                name="payments.create",
                description="Process or create payment",
                category="payments",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
            )
        )


__all__ = ["CapabilityLoader"]

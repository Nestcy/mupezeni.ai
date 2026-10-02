from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ActionPermissionResult:
    allowed: bool
    requires_approval: bool
    action: str
    reason: str | None = None


def evaluate_permission(action: str, enabled: bool, requires_approval: bool) -> ActionPermissionResult:
    if not enabled:
        return ActionPermissionResult(
            allowed=False,
            requires_approval=False,
            action=action,
            reason="Action is disabled by the business configuration.",
        )

    if requires_approval:
        return ActionPermissionResult(
            allowed=True,
            requires_approval=True,
            action=action,
            reason="Action is enabled but requires approval before execution.",
        )

    return ActionPermissionResult(
        allowed=True,
        requires_approval=False,
        action=action,
        reason=None,
    )

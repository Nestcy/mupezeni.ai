from __future__ import annotations

from enum import Enum
from typing import Optional

from app.marketing.models import (
    ActionRisk,
    ApprovalStatus,
    CampaignStatus,
    ContentStatus,
    MarketingApproval,
)
from datetime import datetime


class ApprovalPolicy:
    """
    Determines whether an action requires business approval.
    
    Policy rules determine if an action should wait for human review
    based on risk, type, and business configuration.
    """

    def __init__(self, business_config: dict = None):
        self.business_config = business_config or {}
        self._default_requirements = {
            "publish_social_post": ActionRisk.LOW,
            "publish_organic_post": ActionRisk.LOW,
            "launch_paid_campaign": ActionRisk.HIGH,
            "change_ad_budget": ActionRisk.HIGH,
            "pause_campaign": ActionRisk.MEDIUM,
            "apply_discount": ActionRisk.MEDIUM,
            "create_content_draft": ActionRisk.LOW,
            "create_campaign_plan": ActionRisk.LOW,
        }

    def requires_approval(
        self, action: str, risk_level: ActionRisk, autonomy_level: str
    ) -> bool:
        """
        Determine if an action requires approval based on:
        - Action type
        - Risk level
        - Worker autonomy level
        - Business configuration
        """
        # Supervised: everything requires approval
        if autonomy_level == "supervised":
            return True

        # Autonomous: low risk only
        if autonomy_level == "autonomous":
            return risk_level == ActionRisk.HIGH

        # Bounded (default): medium and high risk require approval
        if autonomy_level == "bounded":
            return risk_level in (ActionRisk.MEDIUM, ActionRisk.HIGH)

        return True

    def get_action_risk(self, action: str) -> ActionRisk:
        """
        Get the risk level for an action.
        """
        return self._default_requirements.get(action, ActionRisk.MEDIUM)


class ApprovalManager:
    """
    Manages approval requests and decisions.
    """

    def __init__(self):
        self._approvals: dict[str, MarketingApproval] = {}

    async def request_approval(
        self,
        business_id: str,
        request_type: str,
        resource_type: str,
        resource_id: str,
        requested_by: str,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> MarketingApproval:
        """
        Create an approval request.
        """
        approval = MarketingApproval(
            id=f"approval_{int(datetime.utcnow().timestamp())}",
            business_id=business_id,
            request_type=request_type,
            resource_type=resource_type,
            resource_id=resource_id,
            requested_by=requested_by,
            reason=reason,
            expires_at=expires_at,
        )
        self._approvals[approval.id] = approval
        return approval

    async def get_approval(self, approval_id: str) -> Optional[MarketingApproval]:
        """
        Get an approval request by ID.
        """
        return self._approvals.get(approval_id)

    async def approve(
        self, approval_id: str, reviewed_by: str, comment: Optional[str] = None
    ) -> Optional[MarketingApproval]:
        """
        Approve an approval request.
        """
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = ApprovalStatus.APPROVED
            approval.reviewed_at = datetime.utcnow()
            approval.reviewed_by = reviewed_by
            approval.review_comment = comment
        return approval

    async def reject(
        self, approval_id: str, reviewed_by: str, comment: Optional[str] = None
    ) -> Optional[MarketingApproval]:
        """
        Reject an approval request.
        """
        approval = self._approvals.get(approval_id)
        if approval:
            approval.status = ApprovalStatus.REJECTED
            approval.reviewed_at = datetime.utcnow()
            approval.reviewed_by = reviewed_by
            approval.review_comment = comment
        return approval

    async def is_approved(
        self, approval_id: str
    ) -> bool:
        """
        Check if an approval has been approved and is not expired.
        """
        approval = self._approvals.get(approval_id)
        if not approval:
            return False

        if approval.status != ApprovalStatus.APPROVED:
            return False

        # Check expiration
        if approval.expires_at and datetime.utcnow() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            return False

        return True

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from app.agents.contracts import WorkerContext
from app.capabilities.models import ActorType
from app.marketing.models import (
    ActionRisk,
    MarketingContent,
    MarketingContext,
)
from app.marketing.approvals import ApprovalManager, ApprovalPolicy
from app.workers.marketing.prompt_builder import MarketingPromptBuilder


class MarketingWorkerService:
    """
    Service for executing the Marketing Worker.

    This is the entry point for marketing operations.
    It orchestrates:
    - Context building
    - Worker definition
    - Prompt building
    - Agent Runtime execution
    - Approval management
    - Response normalization
    """

    def __init__(self, agent_runtime, llm_gateway, worker_registry):
        self.agent_runtime = agent_runtime
        self.llm_gateway = llm_gateway
        self.worker_registry = worker_registry
        self.approval_manager = ApprovalManager()
        self.approval_policy = ApprovalPolicy()

    async def execute(
        self,
        business_id: str,
        message: str,
        marketing_context: Optional[MarketingContext] = None,
        brand_context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Execute the Marketing Worker for a business request.

        Flow:
        1. Load worker definition
        2. Build trusted worker context
        3. Build prompt with marketing/brand context
        4. Execute through Agent Runtime
        5. Manage approval requests
        6. Normalize response
        """
        # Load worker definition
        worker = self.worker_registry.get("marketing")
        if not worker:
            raise ValueError("Marketing Worker not found")

        # Create trusted worker context (backend-generated)
        worker_context = WorkerContext(
            business_id=business_id,
            worker_id="marketing",
            execution_id=f"exec_{int(datetime.utcnow().timestamp())}",
            actor_type=ActorType.AGENT,
            actor_id="worker_marketing",
            conversation_id=f"conv_{int(datetime.utcnow().timestamp())}",
            customer_id=None,  # Marketing worker is business-facing
        )

        # Build system prompt
        prompt_builder = MarketingPromptBuilder(
            worker_instructions=worker.instructions,
            marketing_context=marketing_context,
            brand_context=brand_context,
        )
        system_prompt = prompt_builder.build_system_prompt()

        try:
            # Execute through agent runtime
            # This will be implemented in Phase 4 Agent Runtime
            response_content = "Feature not yet implemented: Agent Runtime integration with Marketing Worker"
            tool_calls = []

            return {
                "execution_id": worker_context.execution_id,
                "business_id": business_id,
                "worker_id": "marketing",
                "worker_version": worker.version,
                "message": response_content,
                "tool_calls": tool_calls,
                "status": "success",
                "metadata": {
                    "worker_id": "marketing",
                    "worker_version": worker.version,
                    "business_id": business_id,
                },
            }
        except Exception as e:
            return {
                "execution_id": worker_context.execution_id,
                "business_id": business_id,
                "worker_id": "marketing",
                "message": "I encountered an issue processing your request. Please try again.",
                "status": "error",
                "error": str(e),
                "metadata": {
                    "worker_id": "marketing",
                    "business_id": business_id,
                },
            }

    async def request_approval_for_action(
        self,
        business_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        risk_level: ActionRisk,
        reason: Optional[str] = None,
        expires_in_minutes: int = 1440,  # 24 hours
    ) -> dict[str, Any]:
        """
        Request approval for a marketing action.
        """
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        approval = await self.approval_manager.request_approval(
            business_id=business_id,
            request_type=action,
            resource_type=resource_type,
            resource_id=resource_id,
            requested_by="worker_marketing",
            reason=reason,
            expires_at=expires_at,
        )

        return {
            "approval_id": approval.id,
            "status": "waiting_for_approval",
            "resource_id": resource_id,
            "action": action,
            "expires_at": expires_at.isoformat(),
        }

    async def get_approval_status(
        self, approval_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get the status of an approval request.
        """
        approval = await self.approval_manager.get_approval(approval_id)
        if not approval:
            return None

        return {
            "approval_id": approval.id,
            "status": approval.status,
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
            "reviewed_by": approval.reviewed_by,
            "review_comment": approval.review_comment,
        }

    async def approve_action(
        self, approval_id: str, reviewed_by: str, comment: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Approve a marketing action (authorized users only).
        """
        approval = await self.approval_manager.approve(
            approval_id, reviewed_by, comment
        )
        if not approval:
            return None

        return {
            "approval_id": approval.id,
            "status": approval.status,
            "reviewed_by": approval.reviewed_by,
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
        }

    async def reject_action(
        self, approval_id: str, reviewed_by: str, comment: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Reject a marketing action (authorized users only).
        """
        approval = await self.approval_manager.reject(
            approval_id, reviewed_by, comment
        )
        if not approval:
            return None

        return {
            "approval_id": approval.id,
            "status": approval.status,
            "reviewed_by": approval.reviewed_by,
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
        }

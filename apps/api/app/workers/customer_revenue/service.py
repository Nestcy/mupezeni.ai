from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.agents.contracts import ActorContext, ActorType, WorkerContext
from app.capabilities.runtime import CapabilityRuntime
from app.workers.customer_revenue.contracts import (
    BrandContext,
    BusinessContext,
    CustomerContext,
    CustomerRevenueWorkerRequest,
    CustomerRevenueWorkerResponse,
)
from app.workers.customer_revenue.prompt_builder import PromptBuilder


class CustomerRevenueWorkerService:
    """
    Service for executing the Customer Revenue Worker.

    This is the entry point for customer conversations.
    It orchestrates:
    - Context building
    - Worker definition
    - Prompt building
    - Agent Runtime execution
    - Response normalization
    """

    def __init__(self, agent_runtime, llm_gateway, worker_registry):
        self.agent_runtime = agent_runtime
        self.llm_gateway = llm_gateway
        self.worker_registry = worker_registry
        self.capability_runtime = CapabilityRuntime()

    async def execute(
        self, request: CustomerRevenueWorkerRequest
    ) -> CustomerRevenueWorkerResponse:
        """
        Execute the Customer Revenue Worker for a customer message.

        Flow:
        1. Load worker definition
        2. Build trusted worker context
        3. Build prompt with business/brand/customer context
        4. Execute through Agent Runtime
        5. Normalize response
        """
        # Load worker definition
        worker = self.worker_registry.get("customer_revenue")
        if not worker:
            raise ValueError("Customer Revenue Worker not found")

        # Create trusted worker context (backend-generated, LLM cannot override)
        worker_context = WorkerContext(
            business_id=request.business_id,
            worker_id="customer_revenue",
            execution_id=f"exec_{datetime.utcnow().timestamp()}",
            actor_type=ActorType.AGENT,
            actor_id="worker_customer_revenue",
            conversation_id=request.customer_message.conversation_id,
            customer_id=request.customer_context.customer_id if request.customer_context else None,
        )

        # Build system prompt
        prompt_builder = PromptBuilder(
            worker_instructions=worker.instructions,
            business_context=request.business_context,
            brand_context=request.brand_context,
            customer_context=request.customer_context,
        )
        system_prompt = prompt_builder.build_system_prompt()

        # Build the full request for Agent Runtime
        # The Agent Runtime will handle:
        # - LLM communication
        # - Tool selection and validation
        # - Capability Runtime execution
        # - Authorization and policy enforcement
        # - Execution logging

        try:
            # Execute through agent runtime
            # (This will be implemented in Phase 4 Agent Runtime)
            response_content = "Feature not yet implemented: Agent Runtime integration"
            tool_calls = []

            return CustomerRevenueWorkerResponse(
                conversation_id=request.customer_message.conversation_id,
                customer_id=request.customer_context.customer_id if request.customer_context else None,
                message=response_content,
                intent="unknown",
                conversation_state="browsing",
                tool_calls=tool_calls,
                execution_id=worker_context.execution_id,
                metadata={
                    "worker_id": "customer_revenue",
                    "worker_version": worker.version,
                    "channel": request.customer_message.channel,
                    "business_id": request.business_id,
                },
            )
        except Exception as e:
            return CustomerRevenueWorkerResponse(
                conversation_id=request.customer_message.conversation_id,
                customer_id=request.customer_context.customer_id if request.customer_context else None,
                message="I encountered an issue processing your request. Please try again.",
                intent="unknown",
                execution_id=worker_context.execution_id,
                metadata={
                    "error": str(e),
                    "worker_id": "customer_revenue",
                },
            )

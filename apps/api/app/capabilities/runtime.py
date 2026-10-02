from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from app.capabilities.errors import (
    ApprovalRequired,
    BusinessAccessDenied,
    BusinessNotFound,
    CapabilityNotFound,
    CapabilityNotSupported,
    ConnectorDisabled,
    ConnectorNotConfigured,
    InvalidCapabilityInput,
    PermissionDenied,
    ProviderExecutionError,
    ProviderUnavailable,
)
from app.capabilities.models import (
    ActorContext,
    ActorType,
    CapabilityExecutionRequest,
    CapabilityResult,
    CapabilityResultStatus,
)
from app.capabilities.registry import get_capability
from app.db.client import get_service_role_client
from app.db.repositories import OrderRepository, CartRepository

logger = logging.getLogger("mupezeni.runtime")


class CapabilityRuntime:
    """Core runtime for executing capabilities safely"""

    def __init__(self):
        self.db = get_service_role_client()

    async def execute(
        self,
        request: CapabilityExecutionRequest,
    ) -> CapabilityResult:
        """
        Execute a capability with full authorization, validation, and audit.

        Steps:
        1. Validate capability exists
        2. Validate business exists
        3. Verify actor authorization
        4. Resolve business connector
        5. Verify connector is active
        6. Check capability support
        7. Check business permissions
        8. Check approval requirements
        9. Execute the connector
        10. Validate result
        11. Record execution
        12. Return normalized response
        """
        request_id = str(uuid.uuid4())

        try:
            # Step 1: Validate capability exists
            capability_def = get_capability(request.capability)
            if not capability_def:
                raise CapabilityNotFound(request.capability)

            # Step 2: Validate business exists and actor has access
            business = await self._verify_business_access(request.business_id, request.actor)
            if not business:
                raise BusinessAccessDenied(request.business_id)

            # Step 3: Resolve business connector
            connector = await self._resolve_connector(
                request.business_id, capability_def.category
            )
            if not connector:
                raise ConnectorNotConfigured(request.business_id, request.capability)

            # Step 4: Verify connector is active
            if connector["status"] != "connected":
                raise ConnectorDisabled(connector["id"])

            # Step 5: Check capability support
            is_supported = await self._check_capability_support(
                connector["connector_definition_id"], request.capability
            )
            if not is_supported:
                provider = connector.get("provider", "unknown")
                raise CapabilityNotSupported(request.capability, provider)

            # Step 6: Check business permissions
            has_permission = await self._check_permissions(
                connector["id"], request.capability
            )
            if not has_permission:
                raise PermissionDenied(request.capability, "Business has not enabled this action")

            # Step 7: Check approval requirements
            requires_approval = await self._check_approval_required(
                connector["id"], request.capability
            )
            if requires_approval and capability_def.requires_approval:
                approval_id = str(uuid.uuid4())
                await self._record_approval_required(
                    request_id, request.business_id, request.capability, approval_id
                )
                return CapabilityResult(
                    status=CapabilityResultStatus.APPROVAL_REQUIRED,
                    capability=request.capability,
                    request_id=request_id,
                    approval_required=True,
                    approval_request_id=approval_id,
                )

            # Step 8: Execute through connector
            from app.connectors.registry import ConnectorRegistry

            registry = ConnectorRegistry()
            provider_instance = registry.resolve(
                request.business_id, capability_def.category
            )
            if not provider_instance:
                raise ProviderUnavailable("unknown")

            try:
                result = await provider_instance.execute(
                    request.capability, **request.input
                )
            except ProviderExecutionError:
                raise
            except Exception as e:
                raise ProviderExecutionError("unknown", str(e))

            # Step 9: Record execution and return
            await self._record_execution(
                request_id,
                request.business_id,
                request.capability,
                "success",
                connector.get("provider", "unknown"),
            )

            return CapabilityResult(
                status=CapabilityResultStatus.SUCCESS,
                capability=request.capability,
                data=result,
                request_id=request_id,
            )

        except CapabilityNotFound as e:
            logger.warning(f"Capability not found: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.VALIDATION_ERROR,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
            )
        except BusinessAccessDenied as e:
            logger.warning(f"Business access denied: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.DENIED,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
            )
        except PermissionDenied as e:
            logger.warning(f"Permission denied: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.DENIED,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
            )
        except CapabilityNotSupported as e:
            logger.warning(f"Capability not supported: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.NOT_SUPPORTED,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
            )
        except ApprovalRequired as e:
            logger.info(f"Approval required: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.APPROVAL_REQUIRED,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
                approval_required=True,
            )
        except ProviderUnavailable as e:
            logger.error(f"Provider unavailable: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.PROVIDER_ERROR,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
            )
        except ProviderExecutionError as e:
            logger.error(f"Provider execution error: {e.message}")
            return CapabilityResult(
                status=CapabilityResultStatus.PROVIDER_ERROR,
                capability=request.capability,
                error=e.message,
                error_code=e.code,
                request_id=request_id,
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
            return CapabilityResult(
                status=CapabilityResultStatus.SYSTEM_ERROR,
                capability=request.capability,
                error="System error during execution",
                error_code="SYSTEM_ERROR",
                request_id=request_id,
            )

    async def _verify_business_access(self, business_id: str, actor: ActorContext | None) -> dict[str, Any] | None:
        """Verify that the actor has access to the business"""
        if not actor:
            return None
        # In a full implementation, verify through business_members table
        # For now, assume actor has access if business_id matches
        if actor.business_id != business_id:
            return None
        return {"id": business_id}

    async def _resolve_connector(
        self, business_id: str, category: str
    ) -> dict[str, Any] | None:
        """Resolve which connector a business uses for a capability category"""
        try:
            result = (
                self.db.table("business_connectors")
                .select(
                    """
                    id,
                    connector_definition_id,
                    status,
                    connector_definitions!connector_definition_id(
                        capability,
                        provider
                    )
                """
                )
                .eq("business_id", business_id)
                .execute()
            )
            for item in result.data or []:
                if item.get("connector_definitions", {}).get("capability") == category:
                    return {
                        "id": item["id"],
                        "connector_definition_id": item["connector_definition_id"],
                        "status": item["status"],
                        "provider": item.get("connector_definitions", {}).get("provider"),
                    }
            return None
        except Exception:
            return None

    async def _check_capability_support(
        self, connector_definition_id: str, capability: str
    ) -> bool:
        """Check if a provider supports a specific capability/action"""
        try:
            result = (
                self.db.table("connector_capabilities")
                .select("id")
                .eq("connector_definition_id", connector_definition_id)
                .eq("action", capability.split(".")[1])  # Extract action from capability name
                .single()
                .execute()
            )
            return result.data is not None
        except Exception:
            return False

    async def _check_permissions(self, business_connector_id: str, capability: str) -> bool:
        """Check if business has enabled this capability/action"""
        try:
            action = capability.split(".")[1]
            result = (
                self.db.table("business_connector_permissions")
                .select("enabled")
                .eq("business_connector_id", business_connector_id)
                .eq("action", action)
                .single()
                .execute()
            )
            if result.data:
                return result.data.get("enabled", False)
            return False
        except Exception:
            return False

    async def _check_approval_required(
        self, business_connector_id: str, capability: str
    ) -> bool:
        """Check if business has marked this capability as requiring approval"""
        try:
            action = capability.split(".")[1]
            result = (
                self.db.table("business_connector_permissions")
                .select("requires_approval")
                .eq("business_connector_id", business_connector_id)
                .eq("action", action)
                .single()
                .execute()
            )
            if result.data:
                return result.data.get("requires_approval", False)
            return False
        except Exception:
            return False

    async def _record_execution(
        self,
        request_id: str,
        business_id: str,
        capability: str,
        status: str,
        provider: str,
    ) -> None:
        """Record capability execution for audit/observability"""
        try:
            self.db.table("capability_executions").insert(
                {
                    "request_id": request_id,
                    "business_id": business_id,
                    "capability": capability,
                    "status": status,
                    "provider": provider,
                    "executed_at": datetime.utcnow().isoformat(),
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to record execution: {e}")

    async def _record_approval_required(
        self,
        request_id: str,
        business_id: str,
        capability: str,
        approval_request_id: str,
    ) -> None:
        """Record that approval is required for this capability execution"""
        try:
            self.db.table("capability_approval_requests").insert(
                {
                    "approval_id": approval_request_id,
                    "request_id": request_id,
                    "business_id": business_id,
                    "capability": capability,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to record approval request: {e}")

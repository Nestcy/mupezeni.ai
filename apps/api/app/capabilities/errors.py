from __future__ import annotations

from enum import Enum


class CapabilityError(Exception):
    """Base capability error"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class CapabilityNotFound(CapabilityError):
    def __init__(self, capability: str):
        super().__init__("CAPABILITY_NOT_FOUND", f"Capability '{capability}' not found")


class BusinessNotFound(CapabilityError):
    def __init__(self, business_id: str):
        super().__init__("BUSINESS_NOT_FOUND", f"Business '{business_id}' not found")


class ConnectorNotConfigured(CapabilityError):
    def __init__(self, business_id: str, capability: str):
        super().__init__(
            "CONNECTOR_NOT_CONFIGURED",
            f"No connector configured for business '{business_id}' and capability '{capability}'",
        )


class ConnectorDisabled(CapabilityError):
    def __init__(self, connector_id: str):
        super().__init__("CONNECTOR_DISABLED", f"Connector '{connector_id}' is disabled")


class CapabilityNotSupported(CapabilityError):
    def __init__(self, capability: str, provider: str):
        super().__init__(
            "CAPABILITY_NOT_SUPPORTED",
            f"Provider '{provider}' does not support capability '{capability}'",
        )


class PermissionDenied(CapabilityError):
    def __init__(self, capability: str, reason: str = ""):
        msg = f"Permission denied for capability '{capability}'"
        if reason:
            msg += f": {reason}"
        super().__init__("PERMISSION_DENIED", msg)


class ApprovalRequired(CapabilityError):
    def __init__(self, capability: str, approval_request_id: str):
        super().__init__(
            "APPROVAL_REQUIRED",
            f"Capability '{capability}' requires approval (request {approval_request_id})",
        )


class InvalidCapabilityInput(CapabilityError):
    def __init__(self, capability: str, validation_error: str):
        super().__init__(
            "INVALID_INPUT",
            f"Invalid input for capability '{capability}': {validation_error}",
        )


class ProviderUnavailable(CapabilityError):
    def __init__(self, provider: str, reason: str = ""):
        msg = f"Provider '{provider}' is unavailable"
        if reason:
            msg += f": {reason}"
        super().__init__("PROVIDER_UNAVAILABLE", msg)


class ProviderExecutionError(CapabilityError):
    def __init__(self, provider: str, error: str):
        super().__init__(
            "PROVIDER_EXECUTION_ERROR",
            f"Provider '{provider}' execution error: {error}",
        )


class BusinessAccessDenied(CapabilityError):
    def __init__(self, business_id: str, reason: str = ""):
        msg = f"Access denied for business '{business_id}'"
        if reason:
            msg += f": {reason}"
        super().__init__("BUSINESS_ACCESS_DENIED", msg)

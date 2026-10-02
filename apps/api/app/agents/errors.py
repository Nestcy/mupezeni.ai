from __future__ import annotations

from enum import Enum


class AgentError(Exception):
    """Base agent error"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class WorkerNotFound(AgentError):
    def __init__(self, worker_id: str):
        super().__init__("WORKER_NOT_FOUND", f"Worker '{worker_id}' not found")


class WorkerDisabled(AgentError):
    def __init__(self, worker_id: str):
        super().__init__("WORKER_DISABLED", f"Worker '{worker_id}' is disabled")


class InvalidToolCall(AgentError):
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            "INVALID_TOOL_CALL", f"Invalid tool call '{tool_name}': {reason}"
        )


class ToolNotAvailable(AgentError):
    def __init__(self, tool_name: str, worker_id: str):
        super().__init__(
            "TOOL_NOT_AVAILABLE",
            f"Tool '{tool_name}' is not available to worker '{worker_id}'",
        )


class ExecutionLimitReached(AgentError):
    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            "EXECUTION_LIMIT_REACHED",
            f"Execution limit reached: {limit_type}={limit_value}",
        )


class LLMProviderError(AgentError):
    def __init__(self, provider: str, error: str):
        super().__init__(
            "LLM_PROVIDER_ERROR", f"LLM provider '{provider}' error: {error}"
        )


class ContextBuildError(AgentError):
    def __init__(self, reason: str):
        super().__init__("CONTEXT_BUILD_ERROR", f"Failed to build context: {reason}")

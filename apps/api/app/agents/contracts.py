from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AutonomyLevel(str, Enum):
    """Worker autonomy classification"""

    SUPERVISED = "supervised"  # high-risk actions require approval
    BOUNDED = "bounded"  # can execute configured low-risk actions
    AUTONOMOUS = "autonomous"  # can execute all permitted actions


class WorkerDefinition(BaseModel):
    """Definition of an AI worker"""

    id: str
    name: str
    purpose: str
    version: str = "1.0"
    instructions: str
    capabilities: list[str] = Field(default_factory=list)
    requires_approval_for: list[str] = Field(default_factory=list)
    autonomy_level: AutonomyLevel = AutonomyLevel.BOUNDED
    max_iterations: int = 10
    max_tool_calls: int = 20
    max_execution_time_seconds: int = 60
    llm_config: Optional[dict[str, Any]] = None
    memory_policy: str = "conversation_buffer"  # conversation_buffer, crm, long_term
    status: str = "active"

    model_config = {"use_enum_values": True}


class WorkerContext(BaseModel):
    """Execution context for a worker (trusted backend-generated)"""

    business_id: str
    worker_id: str
    execution_id: str
    actor_type: str  # agent, human, system
    actor_id: str
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class AgentMessageRole(str, Enum):
    """Role of a message in the agent conversation"""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class AgentMessage(BaseModel):
    """A single message in agent execution"""

    role: AgentMessageRole
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}


class ExecutionStatus(str, Enum):
    """Status of agent execution"""

    RUNNING = "running"
    SUCCESS = "success"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ITERATION_LIMIT = "iteration_limit"
    TOOL_CALL_LIMIT = "tool_call_limit"


class AgentState(BaseModel):
    """Complete state of an agent execution"""

    execution_id: str
    worker: WorkerDefinition
    context: WorkerContext
    messages: list[AgentMessage] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    current_goal: Optional[str] = None
    iteration: int = 0
    status: ExecutionStatus = ExecutionStatus.RUNNING
    final_response: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    model_config = {"use_enum_values": True}

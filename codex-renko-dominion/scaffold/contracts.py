from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    """Return ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class EventType(str, Enum):
    TURN_STARTED = "turn_started"
    CONTEXT_LOADED = "context_loaded"
    MODEL_REQUESTED = "model_requested"
    ASSISTANT_DELTA = "assistant_delta"
    TOOL_REQUESTED = "tool_requested"
    TOOL_APPROVED = "tool_approved"
    TOOL_DENIED = "tool_denied"
    TOOL_COMPLETED = "tool_completed"
    HISTORY_FLUSHED = "history_flushed"
    TURN_COMPLETED = "turn_completed"
    TURN_FAILED = "turn_failed"


class PermissionType(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SPAWN_REMOTE = "spawn_remote"
    MODIFY_SESSION = "modify_session"


@dataclass(frozen=True)
class SessionState:
    session_id: str
    created_at: str
    updated_at: str
    active_model: str
    turn_count: int = 0
    lineage: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TurnRequest:
    session_id: str
    user_input: str
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnResult:
    response: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str
    events: list["RuntimeEvent"] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: EventType
    timestamp: str
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    is_read_only: bool
    is_destructive: bool
    is_concurrency_safe: bool


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    inputs: dict[str, Any]
    caller: str
    session_id: str


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class PermissionRequest:
    actor: str
    action: str
    permission_type: PermissionType
    target: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    request: PermissionRequest


@dataclass(frozen=True)
class ModelRequest:
    model_id: str
    messages: list[dict[str, str]]
    system: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    raw: dict[str, Any] = field(default_factory=dict)

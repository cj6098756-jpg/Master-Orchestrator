"""Session state model for persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from master_orchestrator.models.task import TaskPlan
from master_orchestrator.models.agent_output import AgentReport


@dataclass
class SessionState:
    """Tracks the full state of an orchestration session for persistence."""

    session_id: str
    created_at: str = ""
    last_updated: str = ""
    objective: str = ""
    task_plan: TaskPlan | None = None
    agent_reports: list[AgentReport] = field(default_factory=list)
    iteration_count: int = 0
    status: str = "active"  # active, completed, paused, failed
    sdk_session_id: str | None = None
    cost_usd: float = 0.0
    accumulated_context: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.last_updated:
            self.last_updated = now

    def touch(self):
        """Update the last_updated timestamp."""
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "objective": self.objective,
            "task_plan": self.task_plan.to_dict() if self.task_plan else None,
            "agent_reports": [r.to_dict() for r in self.agent_reports],
            "iteration_count": self.iteration_count,
            "status": self.status,
            "sdk_session_id": self.sdk_session_id,
            "cost_usd": self.cost_usd,
            "accumulated_context": self.accumulated_context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionState:
        task_plan = None
        if data.get("task_plan"):
            task_plan = TaskPlan.from_dict(data["task_plan"])

        return cls(
            session_id=data["session_id"],
            created_at=data.get("created_at", ""),
            last_updated=data.get("last_updated", ""),
            objective=data.get("objective", ""),
            task_plan=task_plan,
            agent_reports=[
                AgentReport.from_dict(r)
                for r in data.get("agent_reports", [])
            ],
            iteration_count=data.get("iteration_count", 0),
            status=data.get("status", "active"),
            sdk_session_id=data.get("sdk_session_id"),
            cost_usd=data.get("cost_usd", 0.0),
            accumulated_context=data.get("accumulated_context", ""),
        )

"""Execution engine data models — tasks, plans, and execution state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """Lifecycle states for a worker task."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"     # Waiting on dependency
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority levels for execution ordering."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WorkerTask:
    """A single executable task for a worker agent.

    This is the TaskEnvelope — every agent gets structured input,
    never a loose string.
    """

    task_id: str = ""
    title: str = ""
    description: str = ""  # Full task description with context
    assigned_agent: str = ""  # Registry key of the agent to execute this
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING

    # Execution context
    source_step: str = ""  # Which recommended_next_step this came from
    source_finding: str = ""  # Which agent finding spawned this
    inputs: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # task_ids

    # Constraints
    allowed_tools: list[str] = field(
        default_factory=lambda: ["Read", "Grep", "Glob"]
    )
    max_turns: int = 15
    cwd: str | None = None

    # Results (populated after execution)
    result: str = ""
    artifacts: list[str] = field(default_factory=list)  # Paths to created files
    error: str | None = None
    confidence: float = 0.0
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task-{uuid.uuid4().hex[:8]}"

    @property
    def is_terminal(self) -> bool:
        """Whether this task is in a terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    @property
    def is_ready(self) -> bool:
        """Whether this task is ready to execute (no unmet dependencies)."""
        return self.status == TaskStatus.PENDING and not self.dependencies

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self, result: str, confidence: float = 0.8) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.confidence = confidence
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "priority": self.priority.value,
            "status": self.status.value,
            "source_step": self.source_step,
            "source_finding": self.source_finding,
            "inputs": self.inputs,
            "dependencies": self.dependencies,
            "allowed_tools": self.allowed_tools,
            "max_turns": self.max_turns,
            "cwd": self.cwd,
            "result": self.result,
            "artifacts": self.artifacts,
            "error": self.error,
            "confidence": self.confidence,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkerTask:
        return cls(
            task_id=data.get("task_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            assigned_agent=data.get("assigned_agent", ""),
            priority=TaskPriority(data.get("priority", "medium")),
            status=TaskStatus(data.get("status", "pending")),
            source_step=data.get("source_step", ""),
            source_finding=data.get("source_finding", ""),
            inputs=data.get("inputs", {}),
            dependencies=data.get("dependencies", []),
            allowed_tools=data.get("allowed_tools", ["Read", "Grep", "Glob"]),
            max_turns=data.get("max_turns", 15),
            cwd=data.get("cwd"),
            result=data.get("result", ""),
            artifacts=data.get("artifacts", []),
            error=data.get("error"),
            confidence=data.get("confidence", 0.0),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
        )


@dataclass
class ExecutionPlan:
    """A structured plan of worker tasks derived from orchestration results.

    This is the bridge between analysis (OrchestrationResult) and
    execution (WorkerTask dispatch).
    """

    plan_id: str = ""
    session_id: str = ""
    objective: str = ""
    tasks: list[WorkerTask] = field(default_factory=list)
    created_at: str = ""
    status: str = "draft"  # draft, approved, executing, completed, failed

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def pending_tasks(self) -> list[WorkerTask]:
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    @property
    def ready_tasks(self) -> list[WorkerTask]:
        """Tasks with no unmet dependencies, ready to execute."""
        completed_ids = {
            t.task_id for t in self.tasks if t.status == TaskStatus.COMPLETED
        }
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            unmet = [d for d in task.dependencies if d not in completed_ids]
            if not unmet:
                ready.append(task)
        return ready

    @property
    def completed_tasks(self) -> list[WorkerTask]:
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]

    @property
    def failed_tasks(self) -> list[WorkerTask]:
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]

    @property
    def is_complete(self) -> bool:
        """All tasks are in a terminal state."""
        return all(t.is_terminal for t in self.tasks) if self.tasks else False

    @property
    def progress(self) -> float:
        """Fraction of tasks completed (0.0 to 1.0)."""
        if not self.tasks:
            return 0.0
        terminal = sum(1 for t in self.tasks if t.is_terminal)
        return terminal / len(self.tasks)

    def summary(self) -> str:
        """One-line progress summary."""
        total = len(self.tasks)
        done = len(self.completed_tasks)
        failed = len(self.failed_tasks)
        return (
            f"[{self.plan_id}] {done}/{total} tasks completed"
            f"{f', {failed} failed' if failed else ''}"
            f" ({self.progress:.0%})"
        )

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "objective": self.objective,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExecutionPlan:
        return cls(
            plan_id=data.get("plan_id", ""),
            session_id=data.get("session_id", ""),
            objective=data.get("objective", ""),
            tasks=[WorkerTask.from_dict(t) for t in data.get("tasks", [])],
            created_at=data.get("created_at", ""),
            status=data.get("status", "draft"),
        )

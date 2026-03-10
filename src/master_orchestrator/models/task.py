"""Task decomposition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    """Classification of task types for agent routing."""

    RESEARCH = "research"
    ANALYSIS = "analysis"
    STRATEGY = "strategy"
    DEVELOPMENT = "development"
    PRODUCT_DESIGN = "product_design"
    WORKFLOW_AUTOMATION = "workflow_automation"
    DECISION_SUPPORT = "decision_support"
    MULTI_DOMAIN = "multi_domain_synthesis"


@dataclass
class SubTask:
    """A single subtask within a task plan."""

    id: str
    description: str
    task_type: TaskType
    assigned_agent: str
    tier: int  # 1 or 2
    dependencies: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed, escalated

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "task_type": self.task_type.value,
            "assigned_agent": self.assigned_agent,
            "tier": self.tier,
            "dependencies": self.dependencies,
            "inputs": self.inputs,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SubTask:
        return cls(
            id=data["id"],
            description=data["description"],
            task_type=TaskType(data["task_type"]),
            assigned_agent=data["assigned_agent"],
            tier=data["tier"],
            dependencies=data.get("dependencies", []),
            inputs=data.get("inputs", {}),
            status=data.get("status", "pending"),
        )


@dataclass
class TaskPlan:
    """Structured plan decomposing a user objective into subtasks."""

    objective: str
    task_types: list[TaskType]
    subtasks: list[SubTask]
    assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)

    @property
    def tier1_subtasks(self) -> list[SubTask]:
        return [s for s in self.subtasks if s.tier == 1]

    @property
    def tier2_subtasks(self) -> list[SubTask]:
        return [s for s in self.subtasks if s.tier == 2]

    @property
    def agent_keys(self) -> list[str]:
        return list({s.assigned_agent for s in self.subtasks})

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "task_types": [t.value for t in self.task_types],
            "subtasks": [s.to_dict() for s in self.subtasks],
            "assumptions": self.assumptions,
            "missing_information": self.missing_information,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaskPlan:
        return cls(
            objective=data["objective"],
            task_types=[TaskType(t) for t in data["task_types"]],
            subtasks=[SubTask.from_dict(s) for s in data["subtasks"]],
            assumptions=data.get("assumptions", []),
            missing_information=data.get("missing_information", []),
        )

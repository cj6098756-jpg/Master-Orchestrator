"""Structured agent output models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentReport:
    """Structured report from a specialist agent.

    Follows the communication protocol:
    Agent Name, Task Assigned, Inputs Used, Assumptions, Findings,
    Risks/Gaps, Confidence Level, Escalation Used, Escalation Notes,
    Recommended Output.
    """

    agent_name: str
    task_assigned: str
    inputs_used: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    findings: str = ""
    risks_and_gaps: list[str] = field(default_factory=list)
    confidence_level: float = 0.0  # 0.0 to 1.0
    escalation_used: bool = False
    escalation_notes: str | None = None
    recommended_output: str = ""

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "task_assigned": self.task_assigned,
            "inputs_used": self.inputs_used,
            "assumptions": self.assumptions,
            "findings": self.findings,
            "risks_and_gaps": self.risks_and_gaps,
            "confidence_level": self.confidence_level,
            "escalation_used": self.escalation_used,
            "escalation_notes": self.escalation_notes,
            "recommended_output": self.recommended_output,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentReport:
        return cls(
            agent_name=data.get("agent_name", "unknown"),
            task_assigned=data.get("task_assigned", ""),
            inputs_used=data.get("inputs_used", []),
            assumptions=data.get("assumptions", []),
            findings=data.get("findings", ""),
            risks_and_gaps=data.get("risks_and_gaps", []),
            confidence_level=float(data.get("confidence_level", 0.0)),
            escalation_used=bool(data.get("escalation_used", False)),
            escalation_notes=data.get("escalation_notes"),
            recommended_output=data.get("recommended_output", ""),
        )

    @property
    def needs_escalation(self) -> bool:
        """Check if this report indicates escalation is needed."""
        return self.escalation_used or self.confidence_level < 0.5

    def summary(self) -> str:
        """One-line summary of the report."""
        esc = " [ESCALATION]" if self.escalation_used else ""
        return (
            f"[{self.agent_name}] confidence={self.confidence_level:.1%} "
            f"risks={len(self.risks_and_gaps)}{esc}"
        )


@dataclass
class OrchestrationResult:
    """Final structured output from a complete orchestration run.

    Follows the 10-section output format:
    1. Objective
    2. Confirmed Inputs
    3. Assumptions
    4. Missing Information
    5. Agent Plan
    6. Specialist Findings
    7. Key Risks/Constraints
    8. Final Synthesis
    9. Recommended Next Steps
    10. Development-Ready Output
    """

    objective: str
    confirmed_inputs: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    agent_plan: list[dict[str, Any]] = field(default_factory=list)
    specialist_findings: list[AgentReport] = field(default_factory=list)
    key_risks: list[str] = field(default_factory=list)
    final_synthesis: str = ""
    recommended_next_steps: list[str] = field(default_factory=list)
    development_ready_output: str | None = None
    iteration_count: int = 0
    session_id: str = ""
    total_cost_usd: float | None = None

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "confirmed_inputs": self.confirmed_inputs,
            "assumptions": self.assumptions,
            "missing_information": self.missing_information,
            "agent_plan": self.agent_plan,
            "specialist_findings": [r.to_dict() for r in self.specialist_findings],
            "key_risks": self.key_risks,
            "final_synthesis": self.final_synthesis,
            "recommended_next_steps": self.recommended_next_steps,
            "development_ready_output": self.development_ready_output,
            "iteration_count": self.iteration_count,
            "session_id": self.session_id,
            "total_cost_usd": self.total_cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OrchestrationResult:
        return cls(
            objective=data["objective"],
            confirmed_inputs=data.get("confirmed_inputs", []),
            assumptions=data.get("assumptions", []),
            missing_information=data.get("missing_information", []),
            agent_plan=data.get("agent_plan", []),
            specialist_findings=[
                AgentReport.from_dict(r)
                for r in data.get("specialist_findings", [])
            ],
            key_risks=data.get("key_risks", []),
            final_synthesis=data.get("final_synthesis", ""),
            recommended_next_steps=data.get("recommended_next_steps", []),
            development_ready_output=data.get("development_ready_output"),
            iteration_count=data.get("iteration_count", 0),
            session_id=data.get("session_id", ""),
            total_cost_usd=data.get("total_cost_usd"),
        )

    @property
    def avg_confidence(self) -> float:
        """Average confidence across all specialist findings."""
        if not self.specialist_findings:
            return 0.0
        total = sum(r.confidence_level for r in self.specialist_findings)
        return total / len(self.specialist_findings)

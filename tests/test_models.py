"""Tests for data models: AgentReport, OrchestrationResult, WorkerTask, ExecutionPlan."""

import pytest
from master_orchestrator.models.agent_output import AgentReport, OrchestrationResult
from master_orchestrator.models.task import SubTask, TaskPlan, TaskType
from master_orchestrator.execution.models import (
    ExecutionPlan,
    TaskPriority,
    TaskStatus,
    WorkerTask,
)


# ---------------------------------------------------------------------------
# AgentReport
# ---------------------------------------------------------------------------

class TestAgentReport:
    def test_defaults(self):
        r = AgentReport(agent_name="test", task_assigned="do stuff")
        assert r.agent_name == "test"
        assert r.confidence_level == 0.0
        assert r.escalation_used is False
        assert r.agent_key == ""
        assert r.tier == 0
        assert r.escalation_resolved is False

    def test_needs_escalation_low_confidence(self):
        r = AgentReport(agent_name="a", task_assigned="t", confidence_level=0.3)
        assert r.needs_escalation is True

    def test_needs_escalation_explicit(self):
        r = AgentReport(
            agent_name="a", task_assigned="t",
            confidence_level=0.9, escalation_used=True,
        )
        assert r.needs_escalation is True

    def test_no_escalation_needed(self):
        r = AgentReport(
            agent_name="a", task_assigned="t",
            confidence_level=0.9, escalation_used=False,
        )
        assert r.needs_escalation is False

    def test_escalation_pending(self):
        r = AgentReport(
            agent_name="a", task_assigned="t",
            confidence_level=0.3, escalation_resolved=False,
        )
        assert r.escalation_pending is True

    def test_escalation_resolved(self):
        r = AgentReport(
            agent_name="a", task_assigned="t",
            confidence_level=0.3, escalation_resolved=True,
        )
        assert r.escalation_pending is False

    def test_roundtrip_dict(self):
        r = AgentReport(
            agent_name="research",
            task_assigned="find data",
            inputs_used=["web"],
            assumptions=["assume valid"],
            findings="found stuff",
            risks_and_gaps=["risk1"],
            confidence_level=0.85,
            escalation_used=False,
            escalation_notes=None,
            recommended_output="do this",
            agent_key="research",
            tier=1,
            escalation_resolved=False,
        )
        d = r.to_dict()
        r2 = AgentReport.from_dict(d)
        assert r2.agent_name == "research"
        assert r2.confidence_level == 0.85
        assert r2.agent_key == "research"
        assert r2.tier == 1

    def test_summary(self):
        r = AgentReport(
            agent_name="research",
            task_assigned="t",
            confidence_level=0.9,
            agent_key="research",
            risks_and_gaps=["a", "b"],
        )
        s = r.summary()
        assert "research" in s
        assert "90" in s  # Handles "90.0%" format
        assert "risks=2" in s


# ---------------------------------------------------------------------------
# OrchestrationResult
# ---------------------------------------------------------------------------

class TestOrchestrationResult:
    def test_avg_confidence_empty(self):
        result = OrchestrationResult(objective="test")
        assert result.avg_confidence == 0.0

    def test_avg_confidence(self):
        reports = [
            AgentReport(agent_name="a", task_assigned="t", confidence_level=0.8),
            AgentReport(agent_name="b", task_assigned="t", confidence_level=0.6),
        ]
        result = OrchestrationResult(
            objective="test",
            specialist_findings=reports,
        )
        assert result.avg_confidence == pytest.approx(0.7)

    def test_roundtrip_dict(self):
        result = OrchestrationResult(
            objective="build something",
            confirmed_inputs=["input1"],
            final_synthesis="done",
            recommended_next_steps=["step1"],
        )
        d = result.to_dict()
        r2 = OrchestrationResult.from_dict(d)
        assert r2.objective == "build something"
        assert r2.final_synthesis == "done"


# ---------------------------------------------------------------------------
# TaskPlan / SubTask
# ---------------------------------------------------------------------------

class TestTaskPlan:
    def test_tier_filtering(self):
        plan = TaskPlan(
            objective="test",
            task_types=[TaskType.RESEARCH, TaskType.DEVELOPMENT],
            subtasks=[
                SubTask(id="1", description="research", task_type=TaskType.RESEARCH,
                        assigned_agent="research", tier=1),
                SubTask(id="2", description="build", task_type=TaskType.DEVELOPMENT,
                        assigned_agent="engineering", tier=1),
                SubTask(id="3", description="api", task_type=TaskType.DEVELOPMENT,
                        assigned_agent="api_design", tier=2),
            ],
        )
        assert len(plan.tier1_subtasks) == 2
        assert len(plan.tier2_subtasks) == 1
        assert set(plan.agent_keys) == {"research", "engineering", "api_design"}


# ---------------------------------------------------------------------------
# WorkerTask
# ---------------------------------------------------------------------------

class TestWorkerTask:
    def test_defaults(self):
        t = WorkerTask(title="do thing", description="detail")
        assert t.task_id.startswith("task-")
        assert t.status == TaskStatus.PENDING
        assert t.is_terminal is False

    def test_lifecycle(self):
        t = WorkerTask(title="do thing", description="detail")
        assert t.is_ready is True  # No dependencies, pending

        t.mark_running()
        assert t.status == TaskStatus.RUNNING
        assert t.started_at != ""

        t.mark_completed("done", 0.9)
        assert t.status == TaskStatus.COMPLETED
        assert t.is_terminal is True
        assert t.confidence == 0.9

    def test_failure(self):
        t = WorkerTask(title="fail", description="will fail")
        t.mark_failed("boom")
        assert t.status == TaskStatus.FAILED
        assert t.error == "boom"
        assert t.is_terminal is True

    def test_dependencies_block_ready(self):
        t = WorkerTask(
            title="blocked",
            description="has deps",
            dependencies=["other-task-id"],
        )
        assert t.is_ready is False

    def test_roundtrip_dict(self):
        t = WorkerTask(
            title="test task",
            description="detail",
            assigned_agent="engineering",
            priority=TaskPriority.HIGH,
        )
        d = t.to_dict()
        t2 = WorkerTask.from_dict(d)
        assert t2.title == "test task"
        assert t2.priority == TaskPriority.HIGH
        assert t2.assigned_agent == "engineering"


# ---------------------------------------------------------------------------
# ExecutionPlan
# ---------------------------------------------------------------------------

class TestExecutionPlan:
    def test_progress(self):
        plan = ExecutionPlan(
            objective="test",
            tasks=[
                WorkerTask(title="a", description="a"),
                WorkerTask(title="b", description="b"),
            ],
        )
        assert plan.progress == 0.0

        plan.tasks[0].mark_completed("done")
        assert plan.progress == pytest.approx(0.5)

        plan.tasks[1].mark_completed("done")
        assert plan.progress == pytest.approx(1.0)
        assert plan.is_complete is True

    def test_ready_tasks_with_deps(self):
        t1 = WorkerTask(title="first", description="a")
        t2 = WorkerTask(
            title="second", description="b",
            dependencies=[t1.task_id],
        )
        plan = ExecutionPlan(objective="test", tasks=[t1, t2])

        ready = plan.ready_tasks
        assert len(ready) == 1
        assert ready[0].task_id == t1.task_id

        # Complete t1
        t1.mark_completed("done")
        ready = plan.ready_tasks
        assert len(ready) == 1
        assert ready[0].task_id == t2.task_id

    def test_roundtrip_dict(self):
        plan = ExecutionPlan(
            objective="test",
            tasks=[WorkerTask(title="a", description="a", assigned_agent="engineering")],
        )
        d = plan.to_dict()
        p2 = ExecutionPlan.from_dict(d)
        assert p2.objective == "test"
        assert len(p2.tasks) == 1
        assert p2.tasks[0].assigned_agent == "engineering"

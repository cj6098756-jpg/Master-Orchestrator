"""Tests for the execution engine models and planner logic."""

import pytest
from master_orchestrator.config import DEFAULT_AGENTS_PATH, load_config
from master_orchestrator.agents.registry import AgentRegistry
from master_orchestrator.execution.models import (
    ExecutionPlan,
    TaskPriority,
    TaskStatus,
    WorkerTask,
)
from master_orchestrator.execution.planner import ExecutionPlanner
from master_orchestrator.agents.dispatch import AgentDispatcher


class TestExecutionPlannerSync:
    """Test the synchronous (no API call) planner methods."""

    def setup_method(self):
        self.config = load_config()
        self.registry = AgentRegistry(DEFAULT_AGENTS_PATH)
        self.dispatcher = AgentDispatcher(self.config, registry=self.registry)
        self.planner = ExecutionPlanner(
            self.config, self.registry, self.dispatcher
        )

    def test_plan_from_steps(self):
        steps = [
            "Implement user authentication with JWT",
            "Write unit tests for the auth module",
            "Deploy to staging environment",
        ]
        plan = self.planner.plan_from_steps(steps, objective="Build auth")
        assert len(plan.tasks) == 3
        assert plan.status == "draft"

    def test_agent_matching_engineering(self):
        key = self.planner._match_agent_to_step("Implement the user authentication module")
        assert key == "engineering"

    def test_agent_matching_research(self):
        key = self.planner._match_agent_to_step("Research best practices for caching")
        assert key == "research"

    def test_agent_matching_testing(self):
        key = self.planner._match_agent_to_step("Write unit tests for the module")
        assert key == "testing"

    def test_agent_matching_devops(self):
        key = self.planner._match_agent_to_step("Deploy using Docker and Kubernetes")
        assert key == "devops"

    def test_agent_matching_security(self):
        key = self.planner._match_agent_to_step("Add authentication and access control")
        assert key == "security"

    def test_agent_matching_database(self):
        key = self.planner._match_agent_to_step("Design database schema for users")
        assert key == "database_schema"

    def test_agent_matching_docs(self):
        key = self.planner._match_agent_to_step("Write documentation and README guide")
        assert key == "documentation"

    def test_tools_for_known_agent(self):
        tools = self.planner._tools_for_agent("engineering")
        assert "Read" in tools
        assert "Edit" in tools
        assert "Write" in tools
        assert "Bash" in tools

    def test_tools_for_unknown_agent(self):
        tools = self.planner._tools_for_agent("nonexistent_agent")
        assert tools == ["Read", "Grep", "Glob"]


class TestExecutionPlanWaves:
    """Test the wave-based execution ordering."""

    def test_dependency_waves(self):
        t1 = WorkerTask(title="setup", description="a", assigned_agent="engineering")
        t2 = WorkerTask(
            title="build", description="b",
            assigned_agent="engineering",
            dependencies=[t1.task_id],
        )
        t3 = WorkerTask(
            title="test", description="c",
            assigned_agent="testing",
            dependencies=[t2.task_id],
        )
        plan = ExecutionPlan(objective="test", tasks=[t1, t2, t3])

        # Wave 1: only t1 is ready
        ready = plan.ready_tasks
        assert len(ready) == 1
        assert ready[0].task_id == t1.task_id

        # Complete t1 → t2 becomes ready
        t1.mark_completed("done")
        ready = plan.ready_tasks
        assert len(ready) == 1
        assert ready[0].task_id == t2.task_id

        # Complete t2 → t3 becomes ready
        t2.mark_completed("done")
        ready = plan.ready_tasks
        assert len(ready) == 1
        assert ready[0].task_id == t3.task_id

        # Complete t3 → plan is complete
        t3.mark_completed("done")
        assert plan.is_complete is True
        assert plan.progress == pytest.approx(1.0)

    def test_parallel_tasks(self):
        """Tasks with no dependencies should all be ready."""
        tasks = [
            WorkerTask(title=f"task-{i}", description=f"d{i}", assigned_agent="engineering")
            for i in range(5)
        ]
        plan = ExecutionPlan(objective="test", tasks=tasks)
        assert len(plan.ready_tasks) == 5

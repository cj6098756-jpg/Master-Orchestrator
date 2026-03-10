"""Task parser — decomposes user objectives into structured task plans."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from master_orchestrator.models.task import TaskPlan, SubTask, TaskType
from master_orchestrator.prompts.templates import build_decomposition_prompt

if TYPE_CHECKING:
    from master_orchestrator.agents.dispatch import AgentDispatcher
    from master_orchestrator.agents.registry import AgentRegistry
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger


class TaskParser:
    """Decomposes user objectives into structured TaskPlan objects.

    Uses a Claude query() call to analyze the objective and assign
    subtasks to appropriate specialist agents.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        config: OrchestratorConfig,
        dispatcher: AgentDispatcher,
        logger: OrchestratorLogger | None = None,
    ):
        self.registry = registry
        self.config = config
        self.dispatcher = dispatcher
        self.logger = logger

    async def parse(self, objective: str) -> TaskPlan:
        """Decompose an objective into a TaskPlan.

        Uses Claude to analyze the objective and produce a structured plan
        with subtask assignments to the available agents.

        Args:
            objective: The user's stated goal.

        Returns:
            A TaskPlan with classified and assigned subtasks.
        """
        # Build the decomposition prompt with available agents
        prompt = build_decomposition_prompt(
            objective=objective,
            tier1_agents=self.registry.tier1_descriptions(),
            tier2_agents=self.registry.tier2_descriptions(),
        )

        if self.logger:
            self.logger.log_event("task_parser", "Decomposing objective into task plan")

        # Use a simple query (no subagents) to decompose the task
        raw_result = await self.dispatcher.dispatch_simple(
            prompt=prompt,
            model=self.config.models.primary,
            max_turns=3,
        )

        # Parse the JSON response into a TaskPlan
        task_plan = self._parse_plan(raw_result, objective)

        if self.logger:
            self.logger.log_task_plan(task_plan)

        return task_plan

    def _parse_plan(self, raw_output: str, objective: str) -> TaskPlan:
        """Parse Claude's response into a TaskPlan.

        Tries multiple extraction strategies:
        1. JSON code block
        2. Raw JSON object
        3. Fallback to a default plan
        """
        # Strategy 1: Extract from JSON code block
        json_match = re.search(
            r'```(?:json)?\s*(\{.*?\})\s*```',
            raw_output,
            re.DOTALL,
        )
        if json_match:
            plan = self._try_parse_json(json_match.group(1), objective)
            if plan:
                return plan

        # Strategy 2: Find the largest JSON object in the output
        json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_output, re.DOTALL)
        for json_str in sorted(json_objects, key=len, reverse=True):
            plan = self._try_parse_json(json_str, objective)
            if plan:
                return plan

        # Strategy 3: Fallback plan
        if self.logger:
            self.logger.log_event(
                "task_parser",
                "Could not parse structured plan; using fallback",
            )
        return self._fallback_plan(objective)

    def _try_parse_json(self, json_text: str, objective: str) -> TaskPlan | None:
        """Attempt to parse JSON text into a TaskPlan."""
        try:
            data = json.loads(json_text)
            if not isinstance(data, dict):
                return None

            subtasks = []
            for st_data in data.get("subtasks", []):
                # Validate assigned agent exists
                agent_key = st_data.get("assigned_agent", "")
                if not self.registry.get(agent_key):
                    # Try to find closest match or use research as default
                    agent_key = "research"

                # Parse task type safely
                try:
                    task_type = TaskType(st_data.get("task_type", "research"))
                except ValueError:
                    task_type = TaskType.RESEARCH

                subtasks.append(SubTask(
                    id=st_data.get("id", f"st-{len(subtasks) + 1}"),
                    description=st_data.get("description", ""),
                    task_type=task_type,
                    assigned_agent=agent_key,
                    tier=int(st_data.get("tier", 1)),
                    dependencies=st_data.get("dependencies", []),
                    inputs=st_data.get("inputs", {}),
                    status="pending",
                ))

            if not subtasks:
                return None

            # Parse task types
            task_types = []
            for t in data.get("task_types", []):
                try:
                    task_types.append(TaskType(t))
                except ValueError:
                    pass
            if not task_types:
                task_types = list({st.task_type for st in subtasks})

            return TaskPlan(
                objective=data.get("objective", objective),
                task_types=task_types,
                subtasks=subtasks,
                assumptions=data.get("assumptions", []),
                missing_information=data.get("missing_information", []),
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _fallback_plan(self, objective: str) -> TaskPlan:
        """Create a simple default plan when parsing fails.

        Assigns the objective to research + engineering agents.
        """
        return TaskPlan(
            objective=objective,
            task_types=[TaskType.RESEARCH, TaskType.DEVELOPMENT],
            subtasks=[
                SubTask(
                    id="st-1",
                    description=f"Research: {objective}",
                    task_type=TaskType.RESEARCH,
                    assigned_agent="research",
                    tier=1,
                ),
                SubTask(
                    id="st-2",
                    description=f"Analyze and design solution for: {objective}",
                    task_type=TaskType.DEVELOPMENT,
                    assigned_agent="systems_architect",
                    tier=1,
                    dependencies=["st-1"],
                ),
                SubTask(
                    id="st-3",
                    description=f"Plan implementation for: {objective}",
                    task_type=TaskType.DEVELOPMENT,
                    assigned_agent="engineering",
                    tier=1,
                    dependencies=["st-1", "st-2"],
                ),
            ],
            assumptions=["Using fallback plan — structured decomposition failed"],
            missing_information=["Full task decomposition was not parseable"],
        )

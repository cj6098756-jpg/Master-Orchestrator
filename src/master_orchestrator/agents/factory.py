"""Agent factory — builds Claude Agent SDK AgentDefinition objects from templates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_agent_sdk import AgentDefinition

from master_orchestrator.agents.registry import AgentRegistry, AgentTemplate
from master_orchestrator.prompts.output_format import AGENT_OUTPUT_INSTRUCTIONS

if TYPE_CHECKING:
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.models.task import TaskPlan


class AgentFactory:
    """Builds Claude Agent SDK AgentDefinition objects from agent templates.

    This is the bridge between the TOML-defined agent configuration
    and the SDK's runtime agent definitions.
    """

    # Windows CLI has an 8191-char limit for command arguments.
    # Keep system prompts well under this to leave room for other params.
    MAX_PROMPT_LENGTH = 4000

    def __init__(self, registry: AgentRegistry, config: OrchestratorConfig):
        self.registry = registry
        self.config = config

    def build_agent(
        self,
        template: AgentTemplate,
        model_override: str | None = None,
    ) -> AgentDefinition:
        """Build a single AgentDefinition from a template.

        Appends structured output instructions to the agent's prompt.
        """
        prompt = self._build_prompt(template)
        model = (
            model_override
            or template.model_override
            or (
                self.config.models.tier1
                if template.tier == 1
                else self.config.models.tier2
            )
        )

        return AgentDefinition(
            description=template.description,
            prompt=prompt,
            tools=template.tools,
            model=model,
        )

    def build_tier1_agents(
        self,
        agent_keys: list[str] | None = None,
    ) -> dict[str, AgentDefinition]:
        """Build AgentDefinitions for Tier 1 specialists.

        Args:
            agent_keys: Specific keys to build. If None, builds all Tier 1.

        Returns:
            Dict mapping agent key to AgentDefinition.
        """
        keys = agent_keys or self.registry.tier1_keys()
        agents = {}
        for key in keys:
            template = self.registry.get_tier1(key)
            if template:
                agents[key] = self.build_agent(template)
        return agents

    def build_tier2_agents(
        self,
        agent_keys: list[str] | None = None,
    ) -> dict[str, AgentDefinition]:
        """Build AgentDefinitions for Tier 2 niche specialists.

        Args:
            agent_keys: Specific keys to build. If None, builds all Tier 2.

        Returns:
            Dict mapping agent key to AgentDefinition.
        """
        keys = agent_keys or self.registry.tier2_keys()
        agents = {}
        for key in keys:
            template = self.registry.get_tier2(key)
            if template:
                agents[key] = self.build_agent(template)
        return agents

    def build_for_task_plan(
        self,
        task_plan: TaskPlan,
    ) -> dict[str, AgentDefinition]:
        """Build all agents needed for a given task plan.

        Selects only the agents assigned in the plan's subtasks.
        """
        tier1_keys = list({
            s.assigned_agent for s in task_plan.subtasks if s.tier == 1
        })
        tier2_keys = list({
            s.assigned_agent for s in task_plan.subtasks if s.tier == 2
        })

        agents = {}
        agents.update(self.build_tier1_agents(tier1_keys))
        agents.update(self.build_tier2_agents(tier2_keys))
        return agents

    def build_escalation_agents(
        self,
        from_agent_keys: list[str],
    ) -> dict[str, AgentDefinition]:
        """Build Tier 2 agents that are escalation targets for given Tier 1 agents.

        Args:
            from_agent_keys: Tier 1 agent keys that need escalation.

        Returns:
            Dict of Tier 2 AgentDefinitions that can address the escalation.
        """
        tier2_keys: set[str] = set()
        for t1_key in from_agent_keys:
            targets = self.registry.get_escalation_targets(t1_key)
            tier2_keys.update(targets)

        return self.build_tier2_agents(list(tier2_keys))

    def _build_prompt(self, template: AgentTemplate) -> str:
        """Build the full prompt: base prompt + output format instructions.

        Truncates if exceeding MAX_PROMPT_LENGTH to respect Windows limits.
        """
        full_prompt = template.prompt + "\n" + AGENT_OUTPUT_INSTRUCTIONS

        if len(full_prompt) > self.MAX_PROMPT_LENGTH:
            # Truncate the base prompt, keep output instructions intact
            available = self.MAX_PROMPT_LENGTH - len(AGENT_OUTPUT_INSTRUCTIONS) - 50
            truncated_base = template.prompt[:available] + "\n[...truncated for length]"
            full_prompt = truncated_base + "\n" + AGENT_OUTPUT_INSTRUCTIONS

        return full_prompt

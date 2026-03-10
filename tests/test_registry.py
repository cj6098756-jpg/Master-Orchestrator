"""Tests for agent registry."""

from master_orchestrator.config import DEFAULT_AGENTS_PATH
from master_orchestrator.agents.registry import AgentRegistry


class TestAgentRegistry:
    def setup_method(self):
        self.registry = AgentRegistry(DEFAULT_AGENTS_PATH)

    def test_tier1_loaded(self):
        agents = self.registry.tier1_agents
        assert len(agents) == 8
        assert "research" in agents
        assert "engineering" in agents
        assert "systems_architect" in agents

    def test_tier2_loaded(self):
        agents = self.registry.tier2_agents
        assert len(agents) == 8
        assert "api_design" in agents
        assert "security" in agents
        assert "testing" in agents

    def test_get_by_key(self):
        t = self.registry.get("research")
        assert t is not None
        assert t.name == "Research Specialist"
        assert t.tier == 1

    def test_resolve_key_direct(self):
        assert self.registry.resolve_key("research") == "research"

    def test_resolve_key_by_name(self):
        assert self.registry.resolve_key("Research Specialist") == "research"

    def test_resolve_key_by_name_case_insensitive(self):
        assert self.registry.resolve_key("research specialist") == "research"

    def test_resolve_key_fuzzy(self):
        # "research" is contained in various strings
        result = self.registry.resolve_key("research")
        assert result == "research"

    def test_resolve_key_unknown(self):
        assert self.registry.resolve_key("totally_unknown_agent_xyz") is None

    def test_escalation_targets(self):
        targets = self.registry.get_escalation_targets("systems_architect")
        assert "api_design" in targets
        assert "frontend_arch" in targets
        assert "database_schema" in targets

    def test_escalation_targets_engineering(self):
        targets = self.registry.get_escalation_targets("engineering")
        assert "api_design" in targets
        assert "security" in targets
        assert "devops" in targets
        assert "testing" in targets

    def test_no_escalation_targets_for_unknown(self):
        targets = self.registry.get_escalation_targets("nonexistent")
        assert targets == []

    def test_summary(self):
        s = self.registry.summary()
        assert "Tier 1" in s
        assert "Tier 2" in s
        assert "research" in s
        assert "16 agents" in s

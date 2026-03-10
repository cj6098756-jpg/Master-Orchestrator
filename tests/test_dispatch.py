"""Tests for agent dispatch — report parsing and key resolution."""

from master_orchestrator.agents.dispatch import AgentDispatcher
from master_orchestrator.agents.registry import AgentRegistry
from master_orchestrator.config import DEFAULT_AGENTS_PATH, load_config
from master_orchestrator.models.agent_output import AgentReport


class TestReportParsing:
    """Test the report parsing logic (no API calls needed)."""

    def setup_method(self):
        self.config = load_config()
        self.registry = AgentRegistry(DEFAULT_AGENTS_PATH)
        self.dispatcher = AgentDispatcher(self.config, registry=self.registry)

    def test_parse_json_code_block(self):
        raw = '''Here are the findings:

```json
{
    "agent_name": "Research Specialist",
    "task_assigned": "Research market size",
    "findings": "The market is growing",
    "confidence_level": 0.85,
    "escalation_used": false,
    "recommended_output": "Market looks good"
}
```

That's the report.'''

        reports = self.dispatcher._parse_agent_reports(raw)
        assert len(reports) == 1
        assert reports[0].agent_name == "Research Specialist"
        assert reports[0].confidence_level == 0.85

    def test_parse_multiple_reports(self):
        raw = '''
```json
{"agent_name": "Agent A", "task_assigned": "t1", "findings": "f1", "confidence_level": 0.9, "escalation_used": false, "recommended_output": "r1"}
```

```json
{"agent_name": "Agent B", "task_assigned": "t2", "findings": "f2", "confidence_level": 0.7, "escalation_used": true, "recommended_output": "r2"}
```
'''
        reports = self.dispatcher._parse_agent_reports(raw)
        assert len(reports) == 2
        assert reports[0].agent_name == "Agent A"
        assert reports[1].agent_name == "Agent B"
        assert reports[1].escalation_used is True

    def test_fallback_report(self):
        raw = "Just some unstructured text without any JSON."
        reports = self.dispatcher._parse_agent_reports(raw)
        assert len(reports) == 1
        assert reports[0].agent_name == "orchestrator_output"
        assert reports[0].confidence_level == 0.5

    def test_empty_input(self):
        reports = self.dispatcher._parse_agent_reports("")
        assert len(reports) == 0


class TestKeyResolution:
    """Test agent key resolution logic."""

    def setup_method(self):
        self.config = load_config()
        self.registry = AgentRegistry(DEFAULT_AGENTS_PATH)
        self.dispatcher = AgentDispatcher(self.config, registry=self.registry)

    def test_resolve_exact_key(self):
        known = {"research", "engineering"}
        assert self.dispatcher._resolve_agent_key("research", known) == "research"

    def test_resolve_display_name_via_known(self):
        known = {"research", "engineering"}
        # "Research Specialist" contains "research"
        result = self.dispatcher._resolve_agent_key("Research Specialist", known)
        assert result == "research"

    def test_resolve_via_registry(self):
        known = set()  # Empty known set, should fall through to registry
        result = self.dispatcher._resolve_agent_key("Research Specialist", known)
        assert result == "research"

    def test_resolve_unknown(self):
        known = set()
        result = self.dispatcher._resolve_agent_key("Totally Unknown Agent XYZ", known)
        assert result is None

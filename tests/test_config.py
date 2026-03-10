"""Tests for configuration loading."""

from pathlib import Path

from master_orchestrator.config import (
    DEFAULT_AGENTS_PATH,
    DEFAULT_CONFIG_PATH,
    OrchestratorConfig,
    load_config,
)


class TestConfig:
    def test_load_defaults(self):
        config = load_config()
        assert config.models.primary == "sonnet"
        assert config.models.tier1 == "sonnet"
        assert config.models.tier2 == "haiku"
        assert config.ralph_loop.max_iterations == 5
        assert config.ralph_loop.quality_threshold == 0.8

    def test_load_overrides(self):
        config = load_config(overrides={
            "model": "opus",
            "max_iterations": 3,
            "verbose": True,
        })
        assert config.models.primary == "opus"
        assert config.ralph_loop.max_iterations == 3
        assert config.verbose is True

    def test_default_paths_exist(self):
        assert DEFAULT_CONFIG_PATH.exists(), f"Config not found: {DEFAULT_CONFIG_PATH}"
        assert DEFAULT_AGENTS_PATH.exists(), f"Agents config not found: {DEFAULT_AGENTS_PATH}"

    def test_nonexistent_config_uses_defaults(self):
        config = load_config(path="/nonexistent/config.toml")
        assert config.models.primary == "sonnet"

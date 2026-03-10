"""Configuration loading and validation."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError(
            "Python < 3.11 requires 'tomli' for TOML support. "
            "Install it with: pip install tomli"
        )


# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.toml"
DEFAULT_AGENTS_PATH = PROJECT_ROOT / "config" / "agents.toml"


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ModelConfig:
    """Model selection for each orchestration tier."""

    primary: str = "sonnet"   # Tier 0 orchestrator
    tier1: str = "sonnet"     # Tier 1 specialists
    tier2: str = "haiku"      # Tier 2 niche specialists (cheaper)
    fallback: str | None = None


@dataclass
class RalphLoopConfig:
    """Ralph Wiggum iterative loop settings."""

    max_iterations: int = 5
    completion_promise: str | None = None
    quality_threshold: float = 0.8  # Confidence threshold for auto-completion


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    log_dir: str = "logs"
    format: str = "markdown"  # markdown or json


@dataclass
class OrchestratorConfig:
    """Top-level orchestrator configuration."""

    models: ModelConfig = field(default_factory=ModelConfig)
    ralph_loop: RalphLoopConfig = field(default_factory=RalphLoopConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    session_dir: str = "sessions"
    permission_mode: str = "acceptEdits"
    max_turns_per_agent: int = 10
    max_budget_usd: float | None = None
    config_path: Path = DEFAULT_CONFIG_PATH
    agents_config_path: Path = DEFAULT_AGENTS_PATH
    cwd: str | None = None
    output_format: str = "markdown"  # markdown or json
    verbose: bool = False


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _deep_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dict keys."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data


def load_config(
    path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> OrchestratorConfig:
    """Load configuration from a TOML file with optional CLI overrides.

    Args:
        path: Path to the TOML config file. Uses default if None.
        overrides: Dict of CLI flag overrides (e.g., {"models.primary": "opus"}).

    Returns:
        Fully populated OrchestratorConfig.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: dict = {}

    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    # Build config from TOML data with defaults
    models = ModelConfig(
        primary=_deep_get(data, "models", "primary", default="sonnet"),
        tier1=_deep_get(data, "models", "tier1", default="sonnet"),
        tier2=_deep_get(data, "models", "tier2", default="haiku"),
        fallback=_deep_get(data, "models", "fallback"),
    )

    ralph_loop = RalphLoopConfig(
        max_iterations=_deep_get(data, "ralph_loop", "max_iterations", default=5),
        completion_promise=_deep_get(data, "ralph_loop", "completion_promise"),
        quality_threshold=_deep_get(
            data, "ralph_loop", "quality_threshold", default=0.8
        ),
    )

    logging_cfg = LoggingConfig(
        level=_deep_get(data, "logging", "level", default="INFO"),
        log_dir=_deep_get(data, "logging", "log_dir", default="logs"),
        format=_deep_get(data, "logging", "format", default="markdown"),
    )

    config = OrchestratorConfig(
        models=models,
        ralph_loop=ralph_loop,
        logging=logging_cfg,
        session_dir=_deep_get(data, "session", "dir", default="sessions"),
        permission_mode=_deep_get(
            data, "orchestrator", "permission_mode", default="acceptEdits"
        ),
        max_turns_per_agent=_deep_get(
            data, "orchestrator", "max_turns_per_agent", default=10
        ),
        max_budget_usd=_deep_get(data, "orchestrator", "max_budget_usd"),
        config_path=config_path,
        agents_config_path=DEFAULT_AGENTS_PATH,
    )

    # Apply CLI overrides
    if overrides:
        if "model" in overrides and overrides["model"]:
            config.models.primary = overrides["model"]
        if "max_iterations" in overrides and overrides["max_iterations"] is not None:
            config.ralph_loop.max_iterations = overrides["max_iterations"]
        if "completion_promise" in overrides and overrides["completion_promise"]:
            config.ralph_loop.completion_promise = overrides["completion_promise"]
        if "verbose" in overrides:
            config.verbose = overrides["verbose"]
        if "output_format" in overrides and overrides["output_format"]:
            config.output_format = overrides["output_format"]
        if "cwd" in overrides and overrides["cwd"]:
            config.cwd = overrides["cwd"]
        if "config" in overrides and overrides["config"]:
            config.config_path = Path(overrides["config"])

    return config

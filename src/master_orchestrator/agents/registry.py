"""Agent template registry — loads agent definitions from agents.toml."""

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
        raise ImportError("Python < 3.11 requires 'tomli'. pip install tomli")


@dataclass
class AgentTemplate:
    """Template for an agent loaded from configuration."""

    key: str
    name: str
    description: str
    prompt: str
    tier: int  # 1 or 2
    tools: list[str] = field(default_factory=lambda: ["Read", "Grep", "Glob"])
    escalation_from: list[str] = field(default_factory=list)
    model_override: str | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "tier": self.tier,
            "tools": self.tools,
            "escalation_from": self.escalation_from,
        }


class AgentRegistry:
    """Registry of all available agent templates, loaded from agents.toml.

    Provides lookup by key, tier, and task type.
    """

    def __init__(self, config_path: Path | str):
        self._tier1: dict[str, AgentTemplate] = {}
        self._tier2: dict[str, AgentTemplate] = {}
        self._load(Path(config_path))

    def _load(self, path: Path) -> None:
        """Load agent templates from a TOML file."""
        if not path.exists():
            raise FileNotFoundError(f"Agent config not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Load Tier 1
        for key, agent_data in data.get("tier1", {}).items():
            self._tier1[key] = AgentTemplate(
                key=key,
                name=agent_data["name"],
                description=agent_data["description"],
                prompt=agent_data["prompt"].strip(),
                tier=1,
                tools=agent_data.get("tools", ["Read", "Grep", "Glob"]),
                escalation_from=[],
                model_override=agent_data.get("model"),
            )

        # Load Tier 2
        for key, agent_data in data.get("tier2", {}).items():
            self._tier2[key] = AgentTemplate(
                key=key,
                name=agent_data["name"],
                description=agent_data["description"],
                prompt=agent_data["prompt"].strip(),
                tier=2,
                tools=agent_data.get("tools", ["Read", "Grep", "Glob"]),
                escalation_from=agent_data.get("escalation_from", []),
                model_override=agent_data.get("model"),
            )

    # --- Tier access ---

    @property
    def tier1_agents(self) -> dict[str, AgentTemplate]:
        """All Tier 1 specialist agents."""
        return dict(self._tier1)

    @property
    def tier2_agents(self) -> dict[str, AgentTemplate]:
        """All Tier 2 niche specialist agents."""
        return dict(self._tier2)

    @property
    def all_agents(self) -> dict[str, AgentTemplate]:
        """All agents across both tiers."""
        return {**self._tier1, **self._tier2}

    # --- Lookup ---

    def get(self, key: str) -> AgentTemplate | None:
        """Get an agent template by key from either tier."""
        return self._tier1.get(key) or self._tier2.get(key)

    def get_tier1(self, key: str) -> AgentTemplate | None:
        """Get a Tier 1 agent by key."""
        return self._tier1.get(key)

    def get_tier2(self, key: str) -> AgentTemplate | None:
        """Get a Tier 2 agent by key."""
        return self._tier2.get(key)

    # --- Query ---

    def tier1_descriptions(self) -> dict[str, str]:
        """Return {key: description} for all Tier 1 agents."""
        return {k: t.description for k, t in self._tier1.items()}

    def tier2_descriptions(self) -> dict[str, str]:
        """Return {key: description} for all Tier 2 agents."""
        return {k: t.description for k, t in self._tier2.items()}

    def resolve_key(self, name_or_key: str) -> str | None:
        """Resolve an agent name or key to a canonical registry key.

        Handles both exact key matches and display name lookups.
        This is critical for escalation routing where agents return
        display names but the registry is indexed by key.
        """
        # Direct key match (fast path)
        if name_or_key in self._tier1 or name_or_key in self._tier2:
            return name_or_key
        # Reverse lookup by display name
        name_lower = name_or_key.lower().strip()
        for key, t in {**self._tier1, **self._tier2}.items():
            if t.name.lower() == name_lower:
                return key
        # Fuzzy: check if the key is contained in the name
        for key, t in {**self._tier1, **self._tier2}.items():
            if key in name_lower or name_lower in key:
                return key
        return None

    def get_escalation_targets(self, tier1_key: str) -> list[str]:
        """Find Tier 2 agents that can be escalated to from a given Tier 1 agent."""
        return [
            key
            for key, t in self._tier2.items()
            if tier1_key in t.escalation_from
        ]

    def tier1_keys(self) -> list[str]:
        return list(self._tier1.keys())

    def tier2_keys(self) -> list[str]:
        return list(self._tier2.keys())

    # --- Display ---

    def summary(self) -> str:
        """Human-readable summary of all registered agents."""
        lines = ["=== Agent Registry ===", ""]
        lines.append("Tier 1 — Specialists:")
        for key, t in sorted(self._tier1.items()):
            lines.append(f"  {key:<22} {t.name:<28} {t.description[:60]}")
        lines.append("")
        lines.append("Tier 2 — Niche Specialists:")
        for key, t in sorted(self._tier2.items()):
            esc = f" (from: {', '.join(t.escalation_from)})" if t.escalation_from else ""
            lines.append(f"  {key:<22} {t.name:<28} {t.description[:50]}{esc}")
        lines.append("")
        lines.append(
            f"Total: {len(self._tier1)} Tier 1 + {len(self._tier2)} Tier 2 "
            f"= {len(self._tier1) + len(self._tier2)} agents"
        )
        return "\n".join(lines)

"""System Status — configuration display and readiness checks."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dashboard import ensure_state

ensure_state()

st.header("\U0001f4ca System Status")
st.caption("Configuration, model settings, and system readiness")

orch = st.session_state.orchestrator
config = st.session_state.config

st.divider()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Configuration")
    st.text(f"Config Path:      {config.config_path}")
    st.text(f"Agents Config:    {config.agents_config_path}")
    st.text(f"Session Dir:      {config.session_dir}")
    st.text(f"Log Dir:          {config.logging.log_dir}")
    st.text(f"Permission Mode:  {config.permission_mode}")
    st.text(f"Max Turns/Agent:  {config.max_turns_per_agent}")

    st.subheader("Models")
    st.text(f"Primary (Tier 0): {config.models.primary}")
    st.text(f"Tier 1:           {config.models.tier1}")
    st.text(f"Tier 2:           {config.models.tier2}")
    st.text(f"Fallback:         {config.models.fallback or '(none)'}")

with col2:
    st.subheader("Ralph Wiggum Loop")
    st.text(f"Max Iterations:     {config.ralph_loop.max_iterations}")
    st.text(f"Quality Threshold:  {config.ralph_loop.quality_threshold:.0%}")
    st.text(f"Completion Promise: {config.ralph_loop.completion_promise or '(none)'}")

    st.subheader("Agent Counts")
    registry = orch.registry
    st.text(f"Tier 1 Specialists:      {len(registry.tier1_agents)}")
    st.text(f"Tier 2 Niche Specialists: {len(registry.tier2_agents)}")
    st.text(f"Total:                   {len(registry.tier1_agents) + len(registry.tier2_agents)}")

    if config.max_budget_usd:
        st.subheader("Budget")
        st.text(f"Budget Limit: ${config.max_budget_usd:.2f}")

st.divider()

# ---------------------------------------------------------------------------
# Connection Checks
# ---------------------------------------------------------------------------

st.subheader("System Checks")

checks = []

# Check Claude Agent SDK
try:
    import claude_agent_sdk
    version = getattr(claude_agent_sdk, "__version__", "unknown")
    checks.append(("Claude Agent SDK", f"Installed (v{version})", True))
except ImportError:
    checks.append(("Claude Agent SDK", "NOT INSTALLED", False))

# Check config file
config_exists = config.config_path.exists() if hasattr(config.config_path, 'exists') else Path(str(config.config_path)).exists()
checks.append(("Config File", f"{'Found' if config_exists else 'NOT FOUND'} ({config.config_path})", config_exists))

# Check agents config
agents_path = Path(str(config.agents_config_path))
agents_exists = agents_path.exists()
checks.append((
    "Agents Config",
    f"{'Found' if agents_exists else 'NOT FOUND'} ({len(registry.tier1_agents) + len(registry.tier2_agents)} agents loaded)",
    agents_exists,
))

# Check sessions dir
sessions_path = Path(config.session_dir)
sessions_exists = sessions_path.exists()
session_count = len(list(sessions_path.glob("*.json"))) if sessions_exists else 0
checks.append((
    "Sessions Dir",
    f"{'Exists' if sessions_exists else 'Not created yet'} ({session_count} sessions)",
    True,  # Not critical
))

# Check logs dir
logs_path = Path(config.logging.log_dir)
logs_exists = logs_path.exists()
checks.append((
    "Logs Dir",
    f"{'Exists' if logs_exists else 'Will be created on first run'}",
    True,
))

# Check Python version
import platform
py_version = platform.python_version()
py_ok = tuple(int(x) for x in py_version.split(".")[:2]) >= (3, 10)
checks.append(("Python", f"{py_version} {'(OK)' if py_ok else '(REQUIRES 3.10+)'}", py_ok))

for name, status, ok in checks:
    icon = "\u2705" if ok else "\u274c"
    st.text(f"  {icon}  {name:<20} {status}")

st.divider()

# ---------------------------------------------------------------------------
# Raw Status Output
# ---------------------------------------------------------------------------

with st.expander("Raw Status Output"):
    st.code(orch.status(), language="text")

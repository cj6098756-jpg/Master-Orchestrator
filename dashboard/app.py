"""Master Orchestrator Dashboard — Streamlit multipage entry point."""

from pathlib import Path
import sys

# Add project paths so all imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Master Orchestrator",
    page_icon="\u2699\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Initialize shared state
# ---------------------------------------------------------------------------

if "orchestrator" not in st.session_state:
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config()
    st.session_state.config = config
    st.session_state.orchestrator = MasterOrchestrator(config)

# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

st.title("\u2699\ufe0f Master Orchestrator")
st.caption(
    "Multi-agent orchestration with Ralph Wiggum iterative loops "
    "| Powered by Claude Agent SDK"
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    registry = st.session_state.orchestrator.registry
    st.metric("Tier 1 Agents", len(registry.tier1_agents))

with col2:
    st.metric("Tier 2 Agents", len(registry.tier2_agents))

with col3:
    sessions = st.session_state.orchestrator.list_sessions(limit=100)
    st.metric("Saved Sessions", len(sessions))

st.divider()

st.markdown("""
### Quick Start

Use the sidebar to navigate between pages:

- **Run Orchestration** -- Enter an objective and run the full multi-agent pipeline
- **Session Explorer** -- View and resume past orchestration sessions
- **Agent Registry** -- Browse all specialist and niche agents
- **System Status** -- Check configuration and system readiness

### How It Works

1. You provide an **objective** (e.g., "Build a REST API for task management")
2. The orchestrator **decomposes** it into subtasks and assigns specialist agents
3. **Tier 1 specialists** analyze the task in parallel
4. If confidence is low, **Tier 2 niche specialists** are escalated
5. The **Ralph Wiggum loop** iterates until quality threshold is met
6. You get a structured **10-section report** with actionable findings
""")

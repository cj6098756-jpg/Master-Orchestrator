"""Agent Registry — browse all specialist and niche agents."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dashboard import ensure_state
from dashboard.components.agent_card import render_agent_card

ensure_state()

st.header("\U0001f916 Agent Registry")
st.caption("Browse Tier 1 specialists and Tier 2 niche specialists")

registry = st.session_state.orchestrator.registry

tab1, tab2, tab_map = st.tabs([
    f"Tier 1 Specialists ({len(registry.tier1_agents)})",
    f"Tier 2 Niche Specialists ({len(registry.tier2_agents)})",
    "Escalation Map",
])

# ---------------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------------

with tab1:
    st.subheader("Tier 1 -- Broad Domain Experts")
    st.caption("Dispatched in Phase 1 of each Ralph Wiggum iteration")

    for key, template in sorted(registry.tier1_agents.items()):
        escalation_targets = registry.get_escalation_targets(key)
        render_agent_card(key, template, escalation_targets=escalation_targets)

# ---------------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Tier 2 -- Deep Domain Experts")
    st.caption("Escalated from Tier 1 when confidence is low or depth is needed")

    for key, template in sorted(registry.tier2_agents.items()):
        render_agent_card(key, template)

# ---------------------------------------------------------------------------
# Escalation Map
# ---------------------------------------------------------------------------

with tab_map:
    st.subheader("Tier 1 \u2192 Tier 2 Escalation Paths")
    st.caption(
        "When a Tier 1 agent reports low confidence, "
        "the orchestrator dispatches the corresponding Tier 2 specialists"
    )

    has_paths = False
    for key in sorted(registry.tier1_agents):
        targets = registry.get_escalation_targets(key)
        t1_name = registry.tier1_agents[key].name

        if targets:
            has_paths = True
            target_names = [
                f"{t} ({registry.tier2_agents[t].name})" for t in targets
                if t in registry.tier2_agents
            ]
            st.markdown(
                f"**{t1_name}** (`{key}`) \u2192 {', '.join(target_names)}"
            )
        else:
            st.text(f"  {t1_name} ({key}) \u2192 (no escalation targets)")

    if not has_paths:
        st.info("No escalation paths configured.")

    st.divider()

    # Summary stats
    col1, col2 = st.columns(2)
    with col1:
        total_paths = sum(
            len(registry.get_escalation_targets(k))
            for k in registry.tier1_agents
        )
        st.metric("Total Escalation Paths", total_paths)
    with col2:
        t2_with_sources = sum(
            1 for t in registry.tier2_agents.values()
            if t.escalation_from
        )
        st.metric("Tier 2 Agents with Sources", t2_with_sources)

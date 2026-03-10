"""Reusable agent template display card."""

from __future__ import annotations

import streamlit as st
from master_orchestrator.agents.registry import AgentTemplate


def render_agent_card(
    key: str,
    template: AgentTemplate,
    escalation_targets: list[str] | None = None,
) -> None:
    """Render an agent template as a Streamlit expander card.

    Args:
        key: Agent registry key.
        template: The AgentTemplate to display.
        escalation_targets: List of Tier 2 agent keys this agent escalates to.
    """
    tier_badge = f"Tier {template.tier}"
    with st.expander(f"**{template.name}** (`{key}`) -- {tier_badge}"):
        st.markdown(f"**Description:** {template.description}")
        st.markdown(f"**Tools:** `{'` `'.join(template.tools)}`")

        if template.tier == 1 and escalation_targets:
            st.markdown(
                f"**Escalates to:** {', '.join(f'`{t}`' for t in escalation_targets)}"
            )

        if template.tier == 2 and template.escalation_from:
            st.markdown(
                f"**Escalation from:** {', '.join(f'`{t}`' for t in template.escalation_from)}"
            )

        if template.model_override:
            st.info(f"Model override: {template.model_override}")

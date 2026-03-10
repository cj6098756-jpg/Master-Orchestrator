"""Reusable OrchestrationResult renderer for the dashboard."""

from __future__ import annotations

import json
import streamlit as st
from master_orchestrator.models.agent_output import OrchestrationResult


def render_result(result: OrchestrationResult) -> None:
    """Render a full OrchestrationResult in the Streamlit page.

    Displays the 10-section structured output with metrics,
    expanders, and formatted markdown.
    """
    # Header metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Iterations", result.iteration_count)
    col2.metric("Agents", len(result.specialist_findings))
    col3.metric("Avg Confidence", f"{result.avg_confidence:.0%}")
    if result.total_cost_usd is not None:
        col4.metric("Cost", f"${result.total_cost_usd:.4f}")
    else:
        col4.metric("Session", result.session_id[:12] if result.session_id else "N/A")

    st.divider()

    # 1. Objective
    st.subheader("1. Objective")
    st.write(result.objective)

    # 2. Confirmed Inputs
    st.subheader("2. Confirmed Inputs")
    if result.confirmed_inputs:
        for ci in result.confirmed_inputs:
            st.write(f"- {ci}")
    else:
        st.caption("(none identified)")

    # 3. Assumptions
    st.subheader("3. Assumptions")
    if result.assumptions:
        for a in result.assumptions:
            st.write(f"- {a}")
    else:
        st.caption("(none)")

    # 4. Missing Information
    st.subheader("4. Missing Information")
    if result.missing_information:
        for mi in result.missing_information:
            st.warning(mi, icon="\u2753")
    else:
        st.caption("(none)")

    # 5. Agent Plan
    st.subheader("5. Agent Plan")
    for ap in result.agent_plan:
        tier = ap.get("tier", "?")
        agent = ap.get("agent", "?")
        task = ap.get("task", "")
        st.write(f"- **[{agent}]** (Tier {tier}): {task}")

    # 6. Specialist Findings
    st.subheader("6. Specialist Findings")
    for report in result.specialist_findings:
        conf = report.confidence_level
        if conf >= 0.8:
            icon = "\u2705"
        elif conf >= 0.5:
            icon = "\u26a0\ufe0f"
        else:
            icon = "\u274c"

        with st.expander(f"{icon} {report.agent_name} -- {conf:.0%} confidence"):
            st.write(f"**Task:** {report.task_assigned}")
            st.markdown(f"**Findings:**\n\n{report.findings}")

            if report.risks_and_gaps:
                st.write("**Risks / Gaps:**")
                for rg in report.risks_and_gaps:
                    st.write(f"- {rg}")

            if report.escalation_used:
                st.error(f"**Escalation:** {report.escalation_notes}")

            if report.recommended_output:
                st.write(f"**Recommendation:** {report.recommended_output}")

    # 7. Key Risks
    st.subheader("7. Key Risks / Constraints")
    if result.key_risks:
        for kr in result.key_risks:
            st.write(f"- {kr}")
    else:
        st.caption("(none identified)")

    # 8. Final Synthesis
    st.subheader("8. Final Synthesis")
    st.markdown(result.final_synthesis)

    # 9. Recommended Next Steps
    st.subheader("9. Recommended Next Steps")
    if result.recommended_next_steps:
        for i, step in enumerate(result.recommended_next_steps, 1):
            st.write(f"{i}. {step}")
    else:
        st.caption("(none)")

    # 10. Development-Ready Output
    st.subheader("10. Development-Ready Output")
    if result.development_ready_output:
        st.code(result.development_ready_output, language="markdown")
    else:
        st.caption("(not applicable or not produced)")

    # Export options
    st.divider()
    with st.expander("Export"):
        st.download_button(
            "Download as JSON",
            data=json.dumps(result.to_dict(), indent=2, default=str),
            file_name=f"orchestration_{result.session_id}.json",
            mime="application/json",
        )

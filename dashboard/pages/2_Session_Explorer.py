"""Session Explorer — list, view, and resume saved sessions."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dashboard import ensure_state
from dashboard.components.result_viewer import render_result

ensure_state()

st.header("\U0001f4c2 Session Explorer")
st.caption("View and resume past orchestration sessions")

orch = st.session_state.orchestrator

# ---------------------------------------------------------------------------
# Session List
# ---------------------------------------------------------------------------

limit = st.slider("Sessions to show", 5, 50, 10)

if st.button("Refresh"):
    st.rerun()

sessions = orch.list_sessions(limit=limit)

if not sessions:
    st.info("No sessions found. Run an orchestration to create one.")
    st.stop()

# Build session table
import json

STATUS_ICONS = {
    "completed": "\u2705",
    "active": "\u25b6\ufe0f",
    "paused": "\u23f8\ufe0f",
    "failed": "\u274c",
}

for s in sessions:
    icon = STATUS_ICONS.get(s["status"], "\u2753")
    col1, col2, col3 = st.columns([1, 4, 2])
    with col1:
        st.write(f"{icon} `{s['session_id']}`")
    with col2:
        st.write(f"**{s['objective']}**")
    with col3:
        st.write(f"Iters: {s['iterations']} | {s['status']}")

st.divider()

# ---------------------------------------------------------------------------
# Session Detail View
# ---------------------------------------------------------------------------

session_ids = [s["session_id"] for s in sessions]
selected = st.selectbox("Select session to view", session_ids)

if selected:
    state = orch.session_manager.load(selected)

    if state is None:
        st.error(f"Session {selected} not found on disk.")
        st.stop()

    tab_overview, tab_reports, tab_json = st.tabs([
        "Overview", "Agent Reports", "Raw JSON"
    ])

    with tab_overview:
        st.subheader("Session Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Objective:** {state.objective}")
            st.write(f"**Status:** {state.status}")
            st.write(f"**Iterations:** {state.iteration_count}")
            st.write(f"**Cost:** ${state.cost_usd:.4f}")
        with col2:
            st.write(f"**Session ID:** `{state.session_id}`")
            st.write(f"**Created:** {state.created_at}")
            st.write(f"**Last Updated:** {state.last_updated}")
            if state.sdk_session_id:
                st.write(f"**SDK Session:** `{state.sdk_session_id}`")

        if state.task_plan:
            st.subheader("Task Plan")
            for st_task in state.task_plan.subtasks:
                st.write(
                    f"- [{st_task.id}] **{st_task.assigned_agent}** "
                    f"(Tier {st_task.tier}): {st_task.description}"
                )

            if state.task_plan.assumptions:
                st.write("**Assumptions:**")
                for a in state.task_plan.assumptions:
                    st.write(f"  - {a}")

            if state.task_plan.missing_information:
                st.write("**Missing Information:**")
                for m in state.task_plan.missing_information:
                    st.warning(m)

    with tab_reports:
        st.subheader(f"Agent Reports ({len(state.agent_reports)})")

        if not state.agent_reports:
            st.info("No agent reports in this session.")
        else:
            for report in state.agent_reports:
                conf = report.confidence_level
                if conf >= 0.8:
                    badge = "\u2705"
                elif conf >= 0.5:
                    badge = "\u26a0\ufe0f"
                else:
                    badge = "\u274c"

                with st.expander(
                    f"{badge} {report.agent_name} -- {conf:.0%} confidence"
                ):
                    st.write(f"**Task:** {report.task_assigned}")
                    st.markdown(f"**Findings:**\n\n{report.findings}")

                    if report.risks_and_gaps:
                        st.write("**Risks:**")
                        for rg in report.risks_and_gaps:
                            st.write(f"- {rg}")

                    if report.escalation_used:
                        st.error(f"Escalation: {report.escalation_notes}")

                    st.write(f"**Recommendation:** {report.recommended_output}")

    with tab_json:
        st.subheader("Raw Session Data")
        st.json(state.to_dict())

    # Resume button
    st.divider()
    if state.status != "completed":
        resume_iters = st.number_input(
            "Additional iterations", min_value=1, max_value=10, value=3
        )
        if st.button("Resume Session", type="primary"):
            from dashboard.bridge import resume_session

            with st.spinner("Resuming orchestration..."):
                try:
                    result = resume_session(selected, resume_iters)
                    st.success("Session resumed successfully!")
                    render_result(result)
                except Exception as e:
                    st.error(f"Resume failed: {e}")

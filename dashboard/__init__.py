"""Streamlit dashboard for the Master Orchestrator."""

import streamlit as st


def ensure_state():
    """Ensure shared session state is initialized.

    In Streamlit multipage apps, pages can be navigated to directly
    (e.g., via URL), bypassing app.py's initialization. This guard
    ensures the orchestrator is always available.
    """
    if "orchestrator" not in st.session_state:
        from master_orchestrator.config import load_config
        from master_orchestrator.orchestrator.core import MasterOrchestrator

        config = load_config()
        st.session_state.config = config
        st.session_state.orchestrator = MasterOrchestrator(config)

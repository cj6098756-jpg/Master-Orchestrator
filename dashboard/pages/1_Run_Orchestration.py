"""Run Orchestration — enter an objective and execute the full pipeline."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dashboard import ensure_state
from dashboard.bridge import run_orchestration
from dashboard.components.result_viewer import render_result

ensure_state()

st.header("\U0001f680 Run Orchestration")
st.caption("Enter an objective and run the multi-agent orchestration pipeline")

# ---------------------------------------------------------------------------
# Objective Input
# ---------------------------------------------------------------------------

objective = st.text_area(
    "Objective",
    placeholder=(
        "Enter your goal, e.g.:\n"
        "  Build a REST API for task management\n"
        "  Design a user authentication system\n"
        "  Analyze the market for AI code assistants"
    ),
    height=120,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

st.subheader("Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    model = st.selectbox(
        "Primary Model",
        ["sonnet", "opus", "haiku"],
        index=0,
        help="The model used for the Tier 0 orchestrator and synthesis",
    )

with col2:
    max_iterations = st.slider(
        "Max Iterations",
        min_value=1,
        max_value=10,
        value=5,
        help="Maximum Ralph Wiggum loop iterations",
    )

with col3:
    quality_threshold = st.slider(
        "Quality Threshold",
        min_value=0.5,
        max_value=1.0,
        value=0.8,
        step=0.05,
        help="Average confidence threshold for auto-completion",
    )

# Advanced settings
with st.expander("Advanced Settings"):
    adv_col1, adv_col2 = st.columns(2)

    with adv_col1:
        cwd = st.text_input(
            "Working Directory",
            value="",
            help="Working directory for agent file operations",
        )
        completion_promise = st.text_input(
            "Completion Promise",
            value="",
            help="Exact string match to trigger loop completion",
        )

    with adv_col2:
        budget = st.number_input(
            "Budget Limit (USD)",
            value=0.0,
            min_value=0.0,
            step=0.50,
            help="Maximum cost for this run (0 = unlimited)",
        )

# ---------------------------------------------------------------------------
# Run Button
# ---------------------------------------------------------------------------

st.divider()

if st.button(
    "Run Orchestration",
    type="primary",
    disabled=not objective.strip(),
    use_container_width=True,
):
    with st.spinner(
        "Running orchestration... This may take several minutes "
        "depending on the number of iterations and agents."
    ):
        try:
            result = run_orchestration(
                objective=objective.strip(),
                model=model,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold,
                cwd=cwd.strip() or None,
                completion_promise=completion_promise.strip() or None,
                budget=budget or None,
            )
            st.session_state.last_result = result
            st.success(
                f"Orchestration complete! "
                f"{result.iteration_count} iterations, "
                f"{len(result.specialist_findings)} agents, "
                f"avg confidence: {result.avg_confidence:.0%}"
            )
        except Exception as e:
            st.error(f"Orchestration failed: {type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# Result Display
# ---------------------------------------------------------------------------

if "last_result" in st.session_state:
    st.divider()
    st.subheader("Results")
    render_result(st.session_state.last_result)

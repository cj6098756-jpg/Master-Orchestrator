from __future__ import annotations

from datetime import datetime, timezone

from scaffold.execution_registry import EXECUTION_REGISTRY
from scaffold.setup import run_setup
from scaffold.tool_pool import assemble_tool_pool


def build_system_init_message() -> str:
    """Build formatted boot banner for runtime startup."""
    ts = datetime.now(timezone.utc).isoformat()
    return (
        "CODEX Renko Dominion v0.1.0\n"
        "==============================\n"
        f"{ts}\n"
        "Subsystems: renko ✓ | codex ✓ | execution ✓ | research ✓ | dashboard ✓\n"
        "Env: see setup output\n"
        f"Execution Registry: IMPL={EXECUTION_REGISTRY['IMPL']} STUB={EXECUTION_REGISTRY['STUB']} MISSING={EXECUTION_REGISTRY['MISSING']}\n"
        "Type 'python main.py --help' for available commands."
    )


def boot() -> str:
    """Run setup and tool assembly, then return the boot banner."""
    run_setup()
    assemble_tool_pool()
    return build_system_init_message()

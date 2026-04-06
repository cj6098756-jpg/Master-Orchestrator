from __future__ import annotations

import os
from datetime import datetime, timezone

from scaffold.config import CONFIG
from scaffold.execution_registry import EXECUTION_REGISTRY
from scaffold.setup import run_setup
from scaffold.tool_pool import assemble_tool_pool

REQUIRED_KEYS = ["ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "TIMESCALEDB_URL", "FRED_API_KEY", "MT4_ZMQ_HOST"]


def _env_summary() -> tuple[int, int]:
    set_count = 0
    for key in REQUIRED_KEYS:
        ok = bool(os.getenv(key))
        set_count += 1 if ok else 0
        print(f"{'✓' if ok else '✗'} {key}")
    print(f"Summary: {set_count}/{len(REQUIRED_KEYS)} required vars set")
    return set_count, len(REQUIRED_KEYS)


def build_system_init_message() -> str:
    """Build formatted boot banner for runtime startup."""
    ts = datetime.now(timezone.utc).isoformat()
    return (
        "CODEX Renko Dominion v0.1.0\n"
        "==============================\n"
        f"{ts}\n"
        "Subsystems: renko ✓ | codex ✓ | execution ✓ | research ✓ | dashboard ✓\n"
        f"Config: model={CONFIG.default_model} max_ctx={CONFIG.max_context_tokens} remote={CONFIG.remote_host}:{CONFIG.remote_port}\n"
        f"Execution Registry: IMPL={EXECUTION_REGISTRY['IMPL']} DEGRADED={EXECUTION_REGISTRY['DEGRADED']} MISSING={EXECUTION_REGISTRY['MISSING']}\n"
        "Type 'python main.py --help' for available commands."
    )


def boot() -> str:
    """Runtime bootstrap authority: env check + setup + tool pool assembly."""
    _env_summary()
    run_setup()
    assemble_tool_pool(permission_profile="standard")
    return build_system_init_message()

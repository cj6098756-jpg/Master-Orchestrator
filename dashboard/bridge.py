"""Async-to-sync bridge for running MasterOrchestrator from Streamlit.

MasterOrchestrator.run() is async, but Streamlit callbacks are sync.
This module bridges that gap using a background thread with its own
event loop to avoid conflicts with Streamlit's internal Tornado loop.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from typing import Any

from master_orchestrator.config import load_config
from master_orchestrator.models.agent_output import OrchestrationResult
from master_orchestrator.orchestrator.core import MasterOrchestrator


def _run_in_thread(
    coro: Any,
    result_queue: queue.Queue,
) -> None:
    """Execute a coroutine in a fresh event loop on a new thread."""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(coro)
        result_queue.put(("ok", result))
    except Exception as e:
        result_queue.put(("error", e))
    finally:
        loop.close()


def run_orchestration(
    objective: str,
    model: str = "sonnet",
    max_iterations: int = 5,
    quality_threshold: float = 0.8,
    cwd: str | None = None,
    completion_promise: str | None = None,
    budget: float | None = None,
) -> OrchestrationResult:
    """Run a full orchestration synchronously (blocking).

    Creates a MasterOrchestrator with the given settings and executes
    the run in a background thread to avoid asyncio event loop conflicts.

    Args:
        objective: The user's goal or task.
        model: Primary model (opus, sonnet, haiku).
        max_iterations: Max Ralph Wiggum loop iterations.
        quality_threshold: Confidence threshold for auto-completion.
        cwd: Working directory for agents.
        completion_promise: Exact string match for loop completion.
        budget: Maximum cost in USD.

    Returns:
        OrchestrationResult with the full 10-section output.

    Raises:
        Exception: If the orchestration fails.
    """
    config = load_config()
    config.models.primary = model
    config.ralph_loop.max_iterations = max_iterations
    config.ralph_loop.quality_threshold = quality_threshold

    if cwd:
        config.cwd = cwd
    if completion_promise:
        config.ralph_loop.completion_promise = completion_promise
    if budget:
        config.max_budget_usd = budget

    orchestrator = MasterOrchestrator(config)

    coro = orchestrator.run(
        objective=objective,
        max_iterations=max_iterations,
        completion_promise=completion_promise,
    )

    result_queue: queue.Queue = queue.Queue()
    thread = threading.Thread(
        target=_run_in_thread,
        args=(coro, result_queue),
        daemon=True,
    )
    thread.start()
    thread.join()

    status, result = result_queue.get()
    if status == "error":
        raise result
    return result


def resume_session(
    session_id: str,
    max_iterations: int | None = None,
) -> OrchestrationResult:
    """Resume a previous orchestration session synchronously.

    Args:
        session_id: ID of the session to resume.
        max_iterations: Additional iterations to run.

    Returns:
        Updated OrchestrationResult.
    """
    config = load_config()
    orchestrator = MasterOrchestrator(config)

    coro = orchestrator.resume(session_id, max_iterations)

    result_queue: queue.Queue = queue.Queue()
    thread = threading.Thread(
        target=_run_in_thread,
        args=(coro, result_queue),
        daemon=True,
    )
    thread.start()
    thread.join()

    status, result = result_queue.get()
    if status == "error":
        raise result
    return result

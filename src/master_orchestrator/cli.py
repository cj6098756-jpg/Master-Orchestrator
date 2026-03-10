"""CLI entry point for the Master Orchestrator.

Usage:
    orchestrate run "Build a REST API for task management"
    orchestrate run "Design a user auth system" --max-iterations 3 --model opus
    orchestrate execute "Build a REST API" --auto
    orchestrate resume abc123def456
    orchestrate sessions
    orchestrate agents --tier 1
    orchestrate status
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from master_orchestrator.utf8 import ensure_utf8


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="orchestrate",
        description=(
            "Master Orchestrator — Multi-agent orchestration "
            "with Ralph Wiggum iterative loops"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  orchestrate run "Build a REST API for task management"\n'
            '  orchestrate run "Design auth system" --max-iterations 3 --model opus\n'
            '  orchestrate execute "Build a REST API" --auto\n'
            "  orchestrate resume abc123def456\n"
            "  orchestrate sessions\n"
            "  orchestrate agents --tier 1\n"
            "  orchestrate status\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # --- run ---
    run_parser = subparsers.add_parser(
        "run",
        help="Run a new orchestration",
        description="Execute a full multi-agent orchestration run.",
    )
    run_parser.add_argument(
        "objective",
        type=str,
        help="The goal or task to orchestrate",
    )
    run_parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        default=None,
        help="Maximum Ralph Wiggum loop iterations (default: from config)",
    )
    run_parser.add_argument(
        "--completion-promise",
        type=str,
        default=None,
        help="Exact string to match for loop completion",
    )
    run_parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        choices=["opus", "sonnet", "haiku"],
        help="Primary model override (default: from config)",
    )
    run_parser.add_argument(
        "--output-format", "-f",
        type=str,
        default=None,
        choices=["markdown", "json"],
        help="Output format (default: markdown)",
    )
    run_parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config file (default: config/default.toml)",
    )
    run_parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory for agents (default: current directory)",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # --- execute ---
    exec_parser = subparsers.add_parser(
        "execute",
        help="Analyze and execute — full pipeline",
        description=(
            "Run analysis (Ralph Wiggum loop), then convert findings "
            "into executable tasks and dispatch worker agents."
        ),
    )
    exec_parser.add_argument(
        "objective",
        type=str,
        help="The goal or task to analyze and execute",
    )
    exec_parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        default=None,
        help="Maximum analysis iterations (default: from config)",
    )
    exec_parser.add_argument(
        "--auto",
        action="store_true",
        default=False,
        help="Auto-approve execution plan without user review",
    )
    exec_parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        choices=["opus", "sonnet", "haiku"],
        help="Primary model override",
    )
    exec_parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config file",
    )
    exec_parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory for agents",
    )
    exec_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # --- resume ---
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume a previous orchestration session",
    )
    resume_parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to resume",
    )
    resume_parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        default=None,
        help="Additional iterations to run",
    )
    resume_parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config file",
    )
    resume_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # --- sessions ---
    sessions_parser = subparsers.add_parser(
        "sessions",
        help="List saved orchestration sessions",
    )
    sessions_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Number of sessions to show (default: 10)",
    )
    sessions_parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config file",
    )

    # --- agents ---
    agents_parser = subparsers.add_parser(
        "agents",
        help="List available agents",
    )
    agents_parser.add_argument(
        "--tier", "-t",
        type=int,
        default=None,
        choices=[1, 2],
        help="Filter by tier (1 or 2)",
    )
    agents_parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config file",
    )

    # --- status ---
    subparsers.add_parser(
        "status",
        help="Check system configuration and readiness",
    )

    return parser


async def cmd_run(args: argparse.Namespace) -> None:
    """Handle the 'run' command."""
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config(
        path=args.config,
        overrides={
            "model": args.model,
            "max_iterations": args.max_iterations,
            "completion_promise": args.completion_promise,
            "output_format": args.output_format,
            "cwd": args.cwd,
            "verbose": args.verbose,
        },
    )

    orchestrator = MasterOrchestrator(config)

    print(f"\n{'=' * 72}")
    print(f"MASTER ORCHESTRATOR — Starting")
    print(f"Objective: {args.objective}")
    print(f"Max iterations: {config.ralph_loop.max_iterations}")
    print(f"Model: {config.models.primary}")
    print(f"{'=' * 72}\n")

    result = await orchestrator.run(
        objective=args.objective,
        max_iterations=args.max_iterations,
        completion_promise=args.completion_promise,
    )

    # Display formatted result
    output = orchestrator.format_result(result, args.output_format)
    print(output)


async def cmd_execute(args: argparse.Namespace) -> None:
    """Handle the 'execute' command — full analyze + execute pipeline."""
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config(
        path=args.config,
        overrides={
            "model": args.model,
            "max_iterations": args.max_iterations,
            "cwd": args.cwd,
            "verbose": args.verbose,
        },
    )

    orchestrator = MasterOrchestrator(config)

    print(f"\n{'=' * 72}")
    print("MASTER ORCHESTRATOR — Analyze & Execute")
    print(f"Objective: {args.objective}")
    print(f"Model: {config.models.primary}")
    print(f"{'=' * 72}\n")

    # Phase 1: Analysis
    print("Phase 1: Analyzing objective...\n")
    result = await orchestrator.run(
        objective=args.objective,
        max_iterations=args.max_iterations,
    )

    # Display analysis report
    output = orchestrator.format_result(result)
    print(output)

    # Phase 2: Plan execution
    print(f"\n{'=' * 72}")
    print("Phase 2: Planning execution...")
    print(f"{'=' * 72}\n")

    plan = await orchestrator.plan_execution(result)
    print(orchestrator.format_plan(plan))

    if not args.auto:
        # Ask for confirmation
        response = input("\nExecute this plan? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Execution cancelled.")
            return

    # Phase 3: Execute
    print(f"\n{'=' * 72}")
    print("Phase 3: Executing tasks...")
    print(f"{'=' * 72}\n")

    executed_plan = await orchestrator.execute(plan)

    # Display results
    print(orchestrator.format_execution_results(executed_plan))

    # Save the plan
    plan_path = orchestrator.execution_engine.save_plan(
        executed_plan, config.session_dir
    )
    print(f"\nExecution plan saved to: {plan_path}")


async def cmd_resume(args: argparse.Namespace) -> None:
    """Handle the 'resume' command."""
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config(
        path=args.config,
        overrides={"verbose": args.verbose},
    )

    orchestrator = MasterOrchestrator(config)

    try:
        result = await orchestrator.resume(
            session_id=args.session_id,
            max_iterations=args.max_iterations,
        )
        output = orchestrator.format_result(result)
        print(output)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_sessions(args: argparse.Namespace) -> None:
    """Handle the 'sessions' command."""
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config(path=args.config)
    orchestrator = MasterOrchestrator(config)

    sessions = orchestrator.list_sessions(limit=args.limit)

    if not sessions:
        print("No sessions found.")
        return

    print(f"\n{'=' * 72}")
    print("ORCHESTRATION SESSIONS")
    print(f"{'=' * 72}\n")

    for s in sessions:
        status_icon = {
            "completed": "+",
            "active": ">",
            "paused": "||",
            "failed": "X",
        }.get(s["status"], "?")

        print(
            f"  [{status_icon}] {s['session_id']:<14} "
            f"iter={s['iterations']:<3} "
            f"{s['status']:<10} "
            f"{s['objective']}"
        )
        print(f"      created: {s['created']}  updated: {s['updated']}")
        print()


async def cmd_agents(args: argparse.Namespace) -> None:
    """Handle the 'agents' command."""
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config(path=args.config)
    orchestrator = MasterOrchestrator(config)
    print(orchestrator.list_agents(tier=args.tier))


async def cmd_status(args: argparse.Namespace) -> None:
    """Handle the 'status' command."""
    from master_orchestrator.config import load_config
    from master_orchestrator.orchestrator.core import MasterOrchestrator

    config = load_config()
    orchestrator = MasterOrchestrator(config)
    print(orchestrator.status())


async def dispatch_command(args: argparse.Namespace) -> None:
    """Route to the correct async handler based on the command."""
    handlers = {
        "run": cmd_run,
        "execute": cmd_execute,
        "resume": cmd_resume,
        "sessions": cmd_sessions,
        "agents": cmd_agents,
        "status": cmd_status,
    }

    handler = handlers.get(args.command)
    if handler:
        await handler(args)
    else:
        build_parser().print_help()


def main():
    """CLI entry point."""
    ensure_utf8()

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        asyncio.run(dispatch_command(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nFATAL ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

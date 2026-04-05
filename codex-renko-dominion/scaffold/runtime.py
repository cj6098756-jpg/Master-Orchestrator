from __future__ import annotations

from dataclasses import dataclass

from codex.doctrine import check_doctrine
from codex.fct import FCTInputs, score_fct
from research.backtest import BacktestConfig, run_backtest
from renko.regime import compute_hurst
from scaffold.command_graph import topological_order
from scaffold.context import ContextManager
from scaffold.contracts import PermissionType, ToolCall, TurnRequest
from scaffold.execution_registry import DEFAULT_EXECUTION_REGISTRY
from scaffold.history import GLOBAL_HISTORY
from scaffold.models import ModelID
from scaffold.query_engine import QueryEnginePort
from scaffold.session_store import StoredSession, append_turn, new_session
from scaffold.tool_pool import assemble_tool_pool


@dataclass
class RuntimeSession:
    session: StoredSession
    context: ContextManager
    model: ModelID
    verbose: bool


class PortRuntime:
    """Local orchestration source-of-truth for runtime flow."""

    def __init__(self):
        self._session: RuntimeSession | None = None
        assemble_tool_pool()

    def boot(self, model: ModelID = ModelID.CLAUDE_SONNET, verbose: bool = False) -> RuntimeSession:
        s = new_session(active_model=model.value)
        self._session = RuntimeSession(s, ContextManager(), model, verbose)
        return self._session

    def _handle_command(self, command: str, args: dict) -> str:
        if command == "fct":
            return str(score_fct(FCTInputs(**args)))
        if command == "hurst":
            return str(compute_hurst(args["prices"]))
        if command == "doctrine":
            return str(check_doctrine(args["action_text"]))
        if command == "backtest":
            return str(run_backtest(args["prices"], BacktestConfig()))
        return ""

    def dispatch(self, command: str, args: dict) -> str:
        """Dispatch command route first; tools only via execution registry."""
        if command in {"fct", "hurst", "doctrine", "backtest"}:
            _ = topological_order(command)
            return self._handle_command(command, args)

        if command == "tool":
            if self._session is None:
                self.boot()
            call = ToolCall(
                tool_name=args["name"],
                inputs=args.get("inputs", {}),
                caller="runtime",
                session_id=self._session.session.session_state.session_id,
            )
            result = DEFAULT_EXECUTION_REGISTRY.dispatch(call)
            return str(result)

        if command == "query":
            if self._session is None:
                self.boot()
            assert self._session is not None
            user_prompt = args["messages"][-1]["content"] if args.get("messages") else ""
            req = TurnRequest(
                session_id=self._session.session.session_state.session_id,
                user_input=user_prompt,
                system_prompt=args.get("system", ""),
                metadata={"permission": PermissionType.MODIFY_SESSION.value},
            )
            qe = QueryEnginePort(self._session.model)
            turn = qe.run_turn(req, messages=args["messages"], tools=args.get("tools"))
            append_turn(self._session.session.session_state.session_id, req, turn)
            GLOBAL_HISTORY.append({"role": "user", "content": user_prompt})
            GLOBAL_HISTORY.append({"role": "assistant", "content": turn.response})
            return turn.response

        return f"Unknown command: {command}"

    def get_session(self) -> RuntimeSession | None:
        return self._session


_RUNTIME: PortRuntime | None = None


def get_runtime() -> PortRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = PortRuntime()
    return _RUNTIME

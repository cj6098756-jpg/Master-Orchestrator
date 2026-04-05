from __future__ import annotations

from dataclasses import dataclass

from codex.doctrine import check_doctrine
from codex.fct import FCTInputs, score_fct
from research.backtest import BacktestConfig, run_backtest
from renko.regime import compute_hurst
from scaffold.context import ContextManager
from scaffold.models import ModelID
from scaffold.query_engine import QueryEnginePort
from scaffold.session_store import StoredSession, new_session


@dataclass
class RuntimeSession:
    session: StoredSession
    context: ContextManager
    model: ModelID
    verbose: bool


class PortRuntime:
    def __init__(self):
        self._session: RuntimeSession | None = None

    def boot(self, model: ModelID = ModelID.CLAUDE_SONNET, verbose: bool = False) -> RuntimeSession:
        s = new_session()
        self._session = RuntimeSession(s, ContextManager(), model, verbose)
        return self._session

    def dispatch(self, command: str, args: dict) -> str:
        if command == "fct":
            return str(score_fct(FCTInputs(**args)))
        if command == "hurst":
            return str(compute_hurst(args["prices"]))
        if command == "doctrine":
            return str(check_doctrine(args["action_text"]))
        if command == "backtest":
            return str(run_backtest(args["prices"], BacktestConfig()))
        if command == "query":
            qe = QueryEnginePort(self._session.model if self._session else ModelID.CLAUDE_SONNET)
            return qe.query(args["messages"], system=args.get("system", "")).response
        return f"Unknown command: {command}"

    def get_session(self) -> RuntimeSession | None:
        return self._session


_RUNTIME: PortRuntime | None = None


def get_runtime() -> PortRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = PortRuntime()
    return _RUNTIME

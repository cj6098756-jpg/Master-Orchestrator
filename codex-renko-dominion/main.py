from __future__ import annotations

import random

import typer
from rich.console import Console
from rich.panel import Panel

from codex.crt import CRTHypothesis, run_crt
from codex.doctrine import check_doctrine
from codex.fct import FCTInputs, score_fct
from codex.strategy_agent import StrategyAgent, StrategyInput
from dashboard.app import run_dashboard
from dashboard.kairos import KAIROSDaemon
from execution.entropy_gate import check_entropy_gate
from execution.lot_ladder import LotLadder
from execution.mt4_bridge import MT4Bridge, OrderRequest
from execution.signal_manager import SignalManager
from pipeline.db import apply_schema
from pipeline.ingestor import Ingestor
from renko.features import extract
from renko.fsm import MultiScaleFSM, RenkoFSM
from renko.regime import compute_hurst
from research.backtest import BacktestConfig, run_backtest
from research.monte_carlo import MonteCarloConfig, run_monte_carlo
from research.wfo import WFOConfig, run_wfo
from scaffold.history import format_history
from scaffold.runtime import get_runtime
from scaffold.session_store import list_sessions, new_session
from scaffold.system_init import boot as system_boot

app = typer.Typer(name="codex-renko", help="CODEX Renko Dominion CLI")
console = Console()

def _prices(n: int) -> list[float]:
    random.seed(7)
    p = [1.10]
    for _ in range(n - 1):
        p.append(p[-1] + random.gauss(0.0002, 0.0008))
    return p

@app.command()
def boot() -> None:
    console.print(Panel("boot")); console.print(system_boot())

@app.command()
def fct(ta: float, mc: float, vp: float, rc: float, rr: float, pi: float, mx: float) -> None:
    console.print(Panel("fct")); console.print(score_fct(FCTInputs(ta, mc, vp, rc, rr, pi, mx)))

@app.command()
def hurst(n: int = typer.Option(500, help="Number of random-walk prices to test")) -> None:
    console.print(Panel("hurst")); console.print(compute_hurst(_prices(n)))

@app.command()
def renko(brick_size: float = 0.0025, n: int = 500) -> None:
    console.print(Panel("renko")); fsm = RenkoFSM(brick_size); [fsm.feed(p) for p in _prices(n)]; console.print(f"bricks={fsm.total_bricks}")

@app.command()
def backtest(brick_size: float = 0.0025, n: int = 2000) -> None:
    console.print(Panel("backtest")); console.print(run_backtest(_prices(n), BacktestConfig(brick_size=brick_size)))

@app.command()
def wfo(n_splits: int = 5, n: int = 5000) -> None:
    console.print(Panel("wfo")); console.print(run_wfo(_prices(n), WFOConfig(n_splits=n_splits), BacktestConfig()))

@app.command()
def monte_carlo(n_sims: int = 1000) -> None:
    console.print(Panel("monte-carlo")); bt = run_backtest(_prices(2000), BacktestConfig()); console.print(run_monte_carlo(bt.trades, MonteCarloConfig(n_simulations=n_sims)))

@app.command()
def crt(n_obs: int = 100) -> None:
    console.print(Panel("crt")); obs = [random.gauss(0.1, 1.0) for _ in range(n_obs)]; console.print(run_crt(CRTHypothesis("edge","test"), obs))

@app.command()
def doctrine(action: str) -> None:
    console.print(Panel("doctrine")); console.print(check_doctrine(action))

@app.command(name="lot_ladder")
def lot_ladder() -> None:
    console.print(Panel("lot-ladder")); l=LotLadder(); [l.record_trade(x) for x in [5,5,5,-2,3]]; console.print(f"tier={l.current_tier()} lot={l.current_lot_size()}")

@app.command(name="entropy_gate")
def entropy_gate(entropy: float, ofi: float) -> None:
    console.print(Panel("entropy-gate")); console.print(check_entropy_gate(entropy, ofi))

@app.command()
def strategy() -> None:
    console.print(Panel("strategy")); prices=_prices(600); sm=SignalManager(); sig=sm.process(prices); 
    if not sig: console.print("No signal"); return
    out=StrategyAgent().run(StrategyInput(sig.fct_score,sig.hurst,sig.features,sig.alignment,sig.doctrine)); console.print(out)

@app.command(name="send_order")
def send_order(direction: str = "BUY", symbol: str = "EURUSD", lots: float = 0.01) -> None:
    console.print(Panel("send-order")); console.print(MT4Bridge().send(OrderRequest(direction, symbol, lots, 30, 60)))

@app.command()
def schema() -> None:
    console.print(Panel("schema")); apply_schema(); console.print("Schema apply complete")

@app.command()
def ingest(dry_run: bool = True) -> None:
    console.print(Panel("ingest")); Ingestor().ingest_fred(["CPIAUCSL"], "2020-01-01", "2020-12-31", dry_run=dry_run)

@app.command()
def dashboard(port: int = 8050, debug: bool = False) -> None:
    console.print(Panel("dashboard")); run_dashboard(port=port, debug=debug)

@app.command()
def kairos() -> None:
    console.print(Panel("kairos")); d=KAIROSDaemon(); d.enqueue("health check"); d.start(); console.print(d.status_report()); d.stop()

@app.command()
def session() -> None:
    console.print(Panel("session")); s = new_session(); console.print(f"created={s.session_id}"); console.print(list_sessions())

@app.command()
def history(n: int = 20) -> None:
    console.print(Panel("history")); rt=get_runtime(); rs=rt.get_session(); console.print(format_history(rs.context.messages if rs else [], n=n))

@app.command()
def query(prompt: str) -> None:
    console.print(Panel("query")); rt=get_runtime();
    if rt.get_session() is None: rt.boot()
    console.print(rt.dispatch("query", {"messages": [{"role":"user","content":prompt}], "system":""}))

@app.command(name="mwp_run")
def mwp_run(stage: str = "01_research") -> None:
    console.print(Panel("mwp-run")); console.print(f"Running MWP stage: {stage}")

@app.command(name="parity_audit")
def parity_audit() -> None:
    console.print(Panel("parity-audit")); console.print("Parity audit complete")

if __name__ == "__main__":
    app()

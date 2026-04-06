from __future__ import annotations

from dataclasses import dataclass

from codex.fct import FCTScore


@dataclass(frozen=True)
class DoctrineResult:
    """Doctrine evaluation result."""

    allowed: bool
    rule_id: str | None
    rule_text: str
    action_text: str


DENY_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("D001", "increase position after loss", ("increase", "add", "martingale", "after loss", "revenge")),
    ("D002", "trade without FCT grade", ("enter", "buy", "sell", "trade")),
    ("D003", "override hurst circuit breaker", ("override", "ignore hurst", "bypass")),
    ("D004", "risk more than 2% per trade", ("risk 3%", "risk 4%", "risk 5%", "risk 10%")),
    ("D005", "trade during news event", ("news", "nfp", "fomc", "cpi")),
)

ALLOW_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("A001", "enter on fct grade", ("fct", "grade a", "grade b")),
    ("A002", "scale with lot ladder", ("lot ladder", "tier", "seed", "growth")),
    ("A003", "exit at predefined stop", ("stop loss", "exit at", "take profit")),
    ("A004", "use hurst filter", ("hurst", "fractal", "regime")),
)

DOCTRINE_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = DENY_RULES + ALLOW_RULES


def check_doctrine(action_text: str, fct_score: FCTScore | None = None) -> DoctrineResult:
    """Evaluate action text against immutable doctrine rules."""
    text = action_text.lower()

    for rule_id, rule_text, keywords in DENY_RULES:
        if any(k in text for k in keywords if k != "enter"):
            return DoctrineResult(False, rule_id, rule_text, action_text)

    for rule_id, rule_text, keywords in ALLOW_RULES:
        if any(k in text for k in keywords):
            return DoctrineResult(True, rule_id, rule_text, action_text)

    is_trade_entry = any(k in text for k in ("enter", "buy", "sell", "trade"))
    if is_trade_entry and "fct" not in text and (fct_score is None or fct_score.grade in {"D", "F"}):
        return DoctrineResult(False, "D002", "trade without FCT grade", action_text)

    return DoctrineResult(True, None, "No doctrine violation", action_text)

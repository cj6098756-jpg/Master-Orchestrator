from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

from codex.doctrine import DoctrineResult
from codex.fct import FCTScore
from renko.features import RenkoFeatures
from renko.fsm import TierAlignment
from renko.regime import HurstResult

MODEL = "qwen/qwen3-32b"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM_PROMPT = """You are the CODEX Strategy Agent for the Renko Dominion system.
You reason about FX trade setups using Renko brick analysis.
You MUST check doctrine before recommending any action.
You MUST require FCT grade A or B before recommending entry.
You MUST require Hurst D >= 1.55 (signal_inhibited=False) before entry.
Output structured JSON only: {\"action\": \"ENTER|WAIT|EXIT\", \"reasoning\": \"...\", \"confidence\": 0.0-1.0}"""


@dataclass(frozen=True)
class StrategyInput:
    """Inputs passed to strategy recommendation endpoint."""

    fct_score: FCTScore
    hurst: HurstResult
    features: RenkoFeatures
    alignment: TierAlignment
    doctrine_check: DoctrineResult


@dataclass(frozen=True)
class StrategyOutput:
    """Structured strategy output."""

    action: str
    reasoning: str
    confidence: float
    raw_response: str


class StrategyAgent:
    """OpenRouter-backed strategy inference client."""

    def _offline_decision(self, payload: StrategyInput, reason: str) -> StrategyOutput:
        action = "WAIT"
        if payload.doctrine_check.allowed and payload.fct_score.is_tradeable() and not payload.hurst.signal_inhibited:
            action = "ENTER" if payload.alignment.aligned else "WAIT"
        return StrategyOutput(action, reason, 0.35 if action == "WAIT" else 0.6, "")

    def run(self, input: StrategyInput) -> StrategyOutput:
        """Call model endpoint, falling back to deterministic local policy if unavailable."""
        if not input.doctrine_check.allowed:
            return StrategyOutput("WAIT", f"Doctrine denied by {input.doctrine_check.rule_id}", 1.0, "")
        if not input.fct_score.is_tradeable():
            return StrategyOutput("WAIT", "FCT grade below tradeable threshold", 1.0, "")
        if input.hurst.signal_inhibited:
            return StrategyOutput("WAIT", "Hurst circuit breaker active (D < 1.55)", 1.0, "")

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return self._offline_decision(input, "Offline policy: OPENROUTER_API_KEY not configured")

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(input, default=str)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(OPENROUTER_URL, json=payload, headers=headers)
                response.raise_for_status()
                raw = response.text
                content = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            return self._offline_decision(input, f"Offline policy: model endpoint unavailable ({exc})")

        try:
            parsed = json.loads(content)
            action = str(parsed.get("action", "WAIT")).upper()
            if action not in {"ENTER", "WAIT", "EXIT"}:
                action = "WAIT"
            return StrategyOutput(
                action=action,
                reasoning=str(parsed.get("reasoning", "")),
                confidence=max(0.0, min(1.0, float(parsed.get("confidence", 0.0)))),
                raw_response=raw,
            )
        except Exception:
            return self._offline_decision(input, "Model response parsing failed; fallback policy applied")

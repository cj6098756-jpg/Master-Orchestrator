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
Output structured JSON only: {"action": "ENTER|WAIT|EXIT", "reasoning": "...", "confidence": 0.0-1.0}"""


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

    def run(self, input: StrategyInput) -> StrategyOutput:
        """Call model endpoint or return STUB when key is missing."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return StrategyOutput("WAIT", "STUB: OPENROUTER_API_KEY not configured", 0.0, "")

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(input, default=str)},
            ],
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()
            raw = response.text
            content = response.json()["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
            return StrategyOutput(
                action=str(parsed.get("action", "WAIT")),
                reasoning=str(parsed.get("reasoning", "")),
                confidence=float(parsed.get("confidence", 0.0)),
                raw_response=raw,
            )
        except Exception:
            return StrategyOutput("WAIT", "Unparseable model response", 0.0, raw)

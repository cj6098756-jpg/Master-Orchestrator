from __future__ import annotations

import os
import time
from dataclasses import dataclass

import anthropic

from scaffold.models import ModelID, get_model_config


@dataclass(frozen=True)
class TurnResult:
    response: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str


class QueryEnginePort:
    def __init__(self, model: ModelID = ModelID.CLAUDE_SONNET):
        self.model = model

    def query(self, messages: list[dict], system: str = "", tools: list[dict] | None = None, max_retries: int = 3) -> TurnResult:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return TurnResult("STUB: ANTHROPIC_API_KEY not configured", 0, 0, 0.0, self.model.value)

        client = anthropic.Anthropic(api_key=api_key)
        for attempt in range(max_retries):
            try:
                resp = client.messages.create(model=self.model.value, max_tokens=1024, system=system, messages=messages, tools=tools or [])
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                in_toks = int(getattr(resp.usage, "input_tokens", 0))
                out_toks = int(getattr(resp.usage, "output_tokens", 0))
                cfg = get_model_config(self.model)
                cost = (in_toks / 1000) * cfg.cost_per_1k_input + (out_toks / 1000) * cfg.cost_per_1k_output
                return TurnResult(text, in_toks, out_toks, cost, self.model.value)
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        return TurnResult("", 0, 0, 0.0, self.model.value)

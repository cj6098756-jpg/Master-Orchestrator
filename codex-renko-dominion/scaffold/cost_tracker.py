from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0

    def record(self, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost_usd
        self.call_count += 1

    def summary(self) -> str:
        return (
            f"calls={self.call_count}, in={self.total_input_tokens}, "
            f"out={self.total_output_tokens}, cost=${self.total_cost_usd:.6f}"
        )

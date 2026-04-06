from __future__ import annotations

from dataclasses import dataclass, field

from scaffold.contracts import RuntimeEvent, utc_now_iso


@dataclass
class CostTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0
    model_usage: dict[str, int] = field(default_factory=dict)
    tool_timings_ms: dict[str, list[float]] = field(default_factory=dict)
    permission_denials: int = 0
    event_log: list[RuntimeEvent] = field(default_factory=list)

    def record(self, input_tokens: int, output_tokens: int, cost_usd: float, model: str | None = None) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost_usd
        self.call_count += 1
        if model:
            self.model_usage[model] = self.model_usage.get(model, 0) + 1

    def record_tool_timing(self, tool_name: str, ms: float) -> None:
        self.tool_timings_ms.setdefault(tool_name, []).append(ms)

    def record_permission_denial(self) -> None:
        self.permission_denials += 1

    def record_event(self, event: RuntimeEvent) -> None:
        self.event_log.append(event)

    def summary(self) -> str:
        return (
            f"calls={self.call_count}, in={self.total_input_tokens}, out={self.total_output_tokens}, "
            f"cost=${self.total_cost_usd:.6f}, denials={self.permission_denials}, ts={utc_now_iso()}"
        )

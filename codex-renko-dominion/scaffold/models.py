from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


class ModelID(str, Enum):
    CLAUDE_OPUS = "claude-opus-4-5"
    CLAUDE_SONNET = "claude-sonnet-4-5"
    CLAUDE_HAIKU = "claude-haiku-3-5"
    QWEN3_32B = "qwen/qwen3-32b"


@dataclass(frozen=True)
class ModelConfig:
    model_id: ModelID
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    provider: str


MODEL_CONFIGS: dict[ModelID, ModelConfig] = {
    ModelID.CLAUDE_OPUS: ModelConfig(ModelID.CLAUDE_OPUS, 200000, 0.015, 0.075, "anthropic"),
    ModelID.CLAUDE_SONNET: ModelConfig(ModelID.CLAUDE_SONNET, 200000, 0.003, 0.015, "anthropic"),
    ModelID.CLAUDE_HAIKU: ModelConfig(ModelID.CLAUDE_HAIKU, 200000, 0.00025, 0.00125, "anthropic"),
    ModelID.QWEN3_32B: ModelConfig(ModelID.QWEN3_32B, 32768, 0.00007, 0.00028, "openrouter"),
}


def estimate_tokens(text: str) -> int:
    """FIX: use char//4, not word-split."""
    return max(1, len(text) // 4)


@lru_cache(maxsize=4)
def get_model_config(model_id: ModelID) -> ModelConfig:
    return MODEL_CONFIGS[model_id]

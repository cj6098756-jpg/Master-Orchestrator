from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    default_model: str = "claude-sonnet-4-5"
    max_context_tokens: int = 180000
    remote_host: str = "0.0.0.0"
    remote_port: int = 8080


CONFIG = RuntimeConfig(
    default_model=os.getenv("CODEX_DEFAULT_MODEL", "claude-sonnet-4-5"),
    max_context_tokens=int(os.getenv("CODEX_MAX_CONTEXT", "180000")),
    remote_host=os.getenv("CODEX_REMOTE_HOST", "0.0.0.0"),
    remote_port=int(os.getenv("CODEX_REMOTE_PORT", "8080")),
)

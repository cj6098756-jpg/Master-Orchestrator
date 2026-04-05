from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class HistoryStore:
    """Durable transcript + searchable recent history."""

    transcript: list[dict] = field(default_factory=list)
    recent_index: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, message: dict, project: str = "default") -> None:
        with self._lock:
            entry = {"project": project, **message}
            self.transcript.append(entry)
            if not self.recent_index or self.recent_index[-1].get("content") != message.get("content"):
                self.recent_index.append(entry)

    def flush_recent(self, project: str | None = None) -> list[dict]:
        with self._lock:
            rows = [r for r in self.recent_index if project is None or r.get("project") == project]
            self.recent_index = []
            return rows


GLOBAL_HISTORY = HistoryStore()


def format_history(messages: list, n: int = 20) -> str:
    """Format recent session history into a compact multiline string."""
    recent = messages[-n:] if len(messages) > n else messages
    lines = [
        f"  [{i+1:03d}] {m['role']:10s} | {m['content'][:80].replace(chr(10), ' ')}..."
        for i, m in enumerate(recent)
    ]
    return "\n".join(lines) if lines else "  (empty history)"

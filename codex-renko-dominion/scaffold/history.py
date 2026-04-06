from __future__ import annotations

import threading
from dataclasses import dataclass, field

from scaffold.contracts import ContextMessage, HistoryRecord, utc_now_iso


@dataclass
class HistoryStore:
    """Searchable index over recent interactions; authoritative turns live in session_store."""

    transcript: list[HistoryRecord] = field(default_factory=list)
    recent_index: list[HistoryRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, session_id: str, message: ContextMessage, project: str = "default") -> None:
        with self._lock:
            entry = HistoryRecord(session_id=session_id, message=message, project=project, timestamp=utc_now_iso())
            self.transcript.append(entry)
            if not self.recent_index or self.recent_index[-1].message.content != message.content:
                self.recent_index.append(entry)

    def flush_recent(self, project: str | None = None) -> list[HistoryRecord]:
        with self._lock:
            rows = [r for r in self.recent_index if project is None or r.project == project]
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

"""JSON file-based session storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SessionStorage:
    """File-based session storage using JSON.

    Each session is stored as a separate JSON file in the base directory.
    Files are named by session_id: {session_id}.json
    """

    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        # Sanitize session_id for filename safety
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.base_dir / f"{safe_id}.json"

    def write(self, session_id: str, data: dict[str, Any]) -> None:
        """Write session data to disk.

        Args:
            session_id: Unique session identifier.
            data: Session data dict to persist.
        """
        path = self._path(session_id)
        path.write_text(
            json.dumps(data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

    def read(self, session_id: str) -> dict[str, Any] | None:
        """Read session data from disk.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session data dict, or None if not found.
        """
        path = self._path(session_id)
        if not path.exists():
            return None

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def exists(self, session_id: str) -> bool:
        """Check if a session exists on disk."""
        return self._path(session_id).exists()

    def delete(self, session_id: str) -> bool:
        """Delete a session from disk.

        Returns True if the session was deleted, False if not found.
        """
        path = self._path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[dict[str, Any]]:
        """List all stored sessions.

        Returns a list of session data dicts, sorted by last_updated
        (most recent first).
        """
        sessions = []
        for path in self.base_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                sessions.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        # Sort by last_updated descending
        sessions.sort(
            key=lambda s: s.get("last_updated", ""),
            reverse=True,
        )

        return sessions

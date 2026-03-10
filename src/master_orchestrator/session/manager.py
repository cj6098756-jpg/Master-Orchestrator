"""Session manager — save, load, list, and resume orchestration sessions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from master_orchestrator.models.session import SessionState
from master_orchestrator.session.storage import SessionStorage

if TYPE_CHECKING:
    from master_orchestrator.config import OrchestratorConfig


class SessionManager:
    """Manages orchestration session persistence.

    Provides high-level operations for saving, loading, listing,
    and resuming sessions using the underlying SessionStorage.
    """

    def __init__(self, config: OrchestratorConfig):
        self.storage = SessionStorage(Path(config.session_dir))

    def save(self, state: SessionState) -> None:
        """Save a session state to disk.

        Args:
            state: The SessionState to persist.
        """
        state.touch()
        self.storage.write(state.session_id, state.to_dict())

    def load(self, session_id: str) -> SessionState | None:
        """Load a previously saved session.

        Args:
            session_id: The session identifier to load.

        Returns:
            SessionState if found, None otherwise.
        """
        data = self.storage.read(session_id)
        if data is None:
            return None
        return SessionState.from_dict(data)

    def list_sessions(self, limit: int = 10) -> list[SessionState]:
        """List recent sessions, most recent first.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of SessionState objects.
        """
        all_data = self.storage.list_all()
        sessions = []
        for data in all_data[:limit]:
            try:
                sessions.append(SessionState.from_dict(data))
            except (KeyError, TypeError):
                continue
        return sessions

    def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return self.storage.exists(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session to delete.

        Returns:
            True if deleted, False if not found.
        """
        return self.storage.delete(session_id)

    def update_status(self, session_id: str, status: str) -> None:
        """Update the status of a session.

        Args:
            session_id: The session to update.
            status: New status (active, completed, paused, failed).
        """
        state = self.load(session_id)
        if state:
            state.status = status
            self.save(state)

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from scaffold.cost_tracker import CostTracker


@dataclass
class StoredSession:
    session_id: str
    messages: list[dict]
    cost_tracker: CostTracker
    created_at: str
    updated_at: str


_SESSIONS: dict[str, StoredSession] = {}


def load_session(session_id: str) -> StoredSession | None:
    return _SESSIONS.get(session_id)


def save_session(session: StoredSession) -> None:
    session.updated_at = datetime.now(timezone.utc).isoformat()
    _SESSIONS[session.session_id] = session


def new_session() -> StoredSession:
    now = datetime.now(timezone.utc).isoformat()
    s = StoredSession(str(uuid.uuid4()), [], CostTracker(), now, now)
    _SESSIONS[s.session_id] = s
    return s


def list_sessions() -> list[str]:
    return list(_SESSIONS.keys())


def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


def persist_to_disk(session: StoredSession, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(session), f, indent=2)


def load_from_disk(path: str) -> StoredSession:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["cost_tracker"] = CostTracker(**data["cost_tracker"])
    return StoredSession(**data)

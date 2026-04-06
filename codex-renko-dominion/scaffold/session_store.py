from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from scaffold.contracts import ContextMessage, RuntimeEvent, SessionState, TurnRequest, TurnResult, utc_now_iso
from scaffold.cost_tracker import CostTracker


@dataclass
class StoredTurn:
    turn_id: str
    request: TurnRequest
    result: TurnResult
    created_at: str
    parent_turn_id: str | None = None
    task_refs: list[str] = field(default_factory=list)


@dataclass
class StoredSession:
    session_state: SessionState
    turns: list[StoredTurn]
    messages: list[ContextMessage]
    cost_tracker: CostTracker
    file_cache_meta: dict[str, str] = field(default_factory=dict)
    @property
    def session_id(self) -> str:
        return self.session_state.session_id

    @property
    def created_at(self) -> str:
        return self.session_state.created_at

    @property
    def updated_at(self) -> str:
        return self.session_state.updated_at


_SESSIONS: dict[str, StoredSession] = {}


def load_session(session_id: str) -> StoredSession | None:
    return _SESSIONS.get(session_id)


def save_session(session: StoredSession) -> None:
    session.session_state = SessionState(
        session_id=session.session_state.session_id,
        created_at=session.session_state.created_at,
        updated_at=utc_now_iso(),
        active_model=session.session_state.active_model,
        turn_count=len(session.turns),
        lineage=session.session_state.lineage,
    )
    _SESSIONS[session.session_state.session_id] = session


def new_session(active_model: str = "claude-sonnet-4-5") -> StoredSession:
    now = utc_now_iso()
    sid = str(uuid.uuid4())
    s = StoredSession(SessionState(sid, now, now, active_model, 0, []), [], [], CostTracker())
    _SESSIONS[sid] = s
    return s


def append_turn(session_id: str, request: TurnRequest, result: TurnResult, task_refs: list[str] | None = None) -> StoredTurn:
    session = _SESSIONS[session_id]
    parent = session.turns[-1].turn_id if session.turns else None
    turn = StoredTurn(str(uuid.uuid4()), request, result, utc_now_iso(), parent, task_refs or [])
    session.turns.append(turn)
    session.messages.append(ContextMessage("user", request.user_input))
    session.messages.append(ContextMessage("assistant", result.response))
    save_session(session)
    return turn


def list_sessions() -> list[str]:
    return list(_SESSIONS.keys())


def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


def snapshot_session(session_id: str) -> dict:
    session = _SESSIONS[session_id]
    return asdict(session)


def resume_session(snapshot: dict) -> StoredSession:
    cost = CostTracker(**snapshot["cost_tracker"])
    state = SessionState(**snapshot["session_state"])
    turns = []
    for t in snapshot["turns"]:
        turns.append(StoredTurn(
            turn_id=t["turn_id"],
            request=TurnRequest(**t["request"]),
            result=TurnResult(**{**t["result"], "events": [RuntimeEvent(**e) for e in t["result"].get("events", [])]}),
            created_at=t["created_at"],
            parent_turn_id=t.get("parent_turn_id"),
            task_refs=t.get("task_refs", []),
        ))
    msgs = [ContextMessage(**m) for m in snapshot["messages"]]
    sess = StoredSession(state, turns, msgs, cost, snapshot.get("file_cache_meta", {}))
    _SESSIONS[state.session_id] = sess
    return sess


def persist_to_disk(session: StoredSession, path: str) -> None:
    Path(path).write_text(json.dumps(asdict(session), indent=2), encoding="utf-8")


def load_from_disk(path: str) -> StoredSession:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return resume_session(data)

from __future__ import annotations

from scaffold.contracts import EventType, PermissionRequest, PermissionType, ToolCall, TurnRequest
from scaffold.execution_registry import ExecutionRegistry
from scaffold.permissions import evaluate
from scaffold.query_engine import QueryEnginePort
from scaffold.runtime import PortRuntime
from scaffold.session_store import append_turn, new_session, snapshot_session
from scaffold.tool_pool import assemble_tool_pool


def test_permission_denial_flow():
    decision = evaluate(PermissionRequest(actor="test", action="rm -rf /", permission_type=PermissionType.EXECUTE))
    assert not decision.allowed


def test_tool_dispatch_flow():
    assemble_tool_pool()
    reg = ExecutionRegistry()
    s = new_session()
    res = reg.dispatch(ToolCall(tool_name="compute_hurst", inputs={"prices": [1, 2, 3, 4, 5, 6]}, caller="t", session_id=s.session_id))
    assert res.ok


def test_event_emission_order():
    qe = QueryEnginePort()
    req = TurnRequest(session_id="s1", user_input="hello")
    events = list(qe.run_turn_stream(req, messages=[{"role": "user", "content": "hello"}]))
    assert events[0].event_type == EventType.TURN_STARTED
    assert events[1].event_type == EventType.CONTEXT_LOADED
    assert events[-1].event_type == EventType.TURN_COMPLETED


def test_session_append_snapshot_resume():
    s = new_session()
    qe = QueryEnginePort()
    req = TurnRequest(session_id=s.session_id, user_input="ping")
    turn = qe.run_turn(req, [{"role": "user", "content": "ping"}])
    append_turn(s.session_id, req, turn)
    snap = snapshot_session(s.session_id)
    assert snap["session_state"]["turn_count"] >= 1


def test_runtime_query_dispatch():
    rt = PortRuntime()
    rt.boot()
    out = rt.dispatch("query", {"messages": [{"role": "user", "content": "status"}], "system": ""})
    assert isinstance(out, str)

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


def test_registry_only_dispatch_denies_unknown_tool():
    reg = ExecutionRegistry()
    s = new_session()
    res = reg.dispatch(ToolCall(tool_name="nope", inputs={}, caller="t", session_id=s.session_id))
    assert not res.ok


def test_remote_transport_parity_contract_shape():
    from scaffold.remote_runtime import run_ssh_mode, run_teleport_mode

    ssh_result = run_ssh_mode("localhost", "nobody", "echo ok")
    tel_result = run_teleport_mode("cluster", "echo ok")
    assert isinstance(ssh_result, str)
    assert isinstance(tel_result, str)


def test_history_flush_reload_semantics():
    from scaffold.history import GLOBAL_HISTORY
    from scaffold.contracts import ContextMessage

    GLOBAL_HISTORY.append("s-x", ContextMessage("user", "one"), project="p")
    GLOBAL_HISTORY.append("s-x", ContextMessage("assistant", "two"), project="p")
    rows = GLOBAL_HISTORY.flush_recent(project="p")
    assert len(rows) >= 2

from __future__ import annotations

import os
import time
from typing import Iterator

import importlib

from scaffold.contracts import (
    EventType,
    ModelRequest,
    ModelResponse,
    RuntimeEvent,
    TurnRequest,
    TurnResult,
    utc_now_iso,
)
from scaffold.models import ModelID, get_model_config


class QueryEnginePort:
    """Event-stream query engine used as runtime execution spine."""

    def __init__(self, model: ModelID = ModelID.CLAUDE_SONNET):
        self.model = model

    def _event(self, event_type: EventType, session_id: str, **payload: object) -> RuntimeEvent:
        return RuntimeEvent(event_type=event_type, timestamp=utc_now_iso(), session_id=session_id, payload=dict(payload))

    def _run_model(self, req: ModelRequest, max_retries: int = 3) -> ModelResponse:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return ModelResponse(text="Offline mode: ANTHROPIC_API_KEY not configured", input_tokens=0, output_tokens=0, raw={})

        anthropic_mod = importlib.import_module("anthropic")
        client = anthropic_mod.Anthropic(api_key=api_key)
        for attempt in range(max_retries):
            try:
                resp = client.messages.create(
                    model=req.model_id,
                    max_tokens=1024,
                    system=req.system,
                    messages=req.messages,
                    tools=req.tools,
                )
                text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
                return ModelResponse(
                    text=text,
                    input_tokens=int(getattr(resp.usage, "input_tokens", 0)),
                    output_tokens=int(getattr(resp.usage, "output_tokens", 0)),
                    raw={"id": getattr(resp, "id", "")},
                )
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Model call failed: {exc}") from exc
                time.sleep(2 ** attempt)
        return ModelResponse(text="", input_tokens=0, output_tokens=0, raw={})

    def run_turn_stream(self, request: TurnRequest, messages: list[dict[str, str]], tools: list[dict] | None = None) -> Iterator[RuntimeEvent]:
        """Yield typed runtime events in deterministic order for one turn."""
        sid = request.session_id
        yield self._event(EventType.TURN_STARTED, sid, user_input=request.user_input)
        yield self._event(EventType.CONTEXT_LOADED, sid, message_count=len(messages))

        model_req = ModelRequest(model_id=self.model.value, messages=messages, system=request.system_prompt, tools=tools or [])
        yield self._event(EventType.MODEL_REQUESTED, sid, model=self.model.value)
        model_resp = self._run_model(model_req)

        if model_resp.text:
            yield self._event(EventType.ASSISTANT_DELTA, sid, delta=model_resp.text)

        yield self._event(
            EventType.TURN_COMPLETED,
            sid,
            input_tokens=model_resp.input_tokens,
            output_tokens=model_resp.output_tokens,
        )

    def run_turn(self, request: TurnRequest, messages: list[dict[str, str]], tools: list[dict] | None = None) -> TurnResult:
        """Execute one turn and return final TurnResult with captured events."""
        events = list(self.run_turn_stream(request, messages, tools))
        completed = next(e for e in reversed(events) if e.event_type == EventType.TURN_COMPLETED)
        delta = next((e.payload["delta"] for e in events if e.event_type == EventType.ASSISTANT_DELTA), "")
        cfg = get_model_config(self.model)
        in_toks = int(completed.payload.get("input_tokens", 0))
        out_toks = int(completed.payload.get("output_tokens", 0))
        cost = (in_toks / 1000) * cfg.cost_per_1k_input + (out_toks / 1000) * cfg.cost_per_1k_output
        return TurnResult(response=delta, input_tokens=in_toks, output_tokens=out_toks, cost_usd=cost, model=self.model.value, events=events)

    def query(self, messages: list[dict], system: str = "", tools: list[dict] | None = None, max_retries: int = 3) -> TurnResult:
        """Backward-compatible facade preserving previous public API."""
        req = TurnRequest(session_id="standalone", user_input=messages[-1]["content"] if messages else "", system_prompt=system)
        _ = max_retries
        return self.run_turn(req, messages=messages, tools=tools)

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import zmq


@dataclass(frozen=True)
class OrderRequest:
    """Outgoing MT4 order instruction."""

    action: str
    symbol: str
    lots: float
    sl_pips: int
    tp_pips: int


@dataclass(frozen=True)
class OrderResult:
    """Result of MT4 bridge send attempt."""

    sent: bool
    message: str
    request: OrderRequest


class MT4Bridge:
    """ZeroMQ PUSH bridge to MT4 terminal integration."""

    def send(self, request: OrderRequest) -> OrderResult:
        """Send order JSON to MT4, or return STUB if env is missing."""
        host = os.getenv("MT4_ZMQ_HOST")
        port = int(os.getenv("MT4_ZMQ_PORT", "5555"))
        if not host:
            return OrderResult(False, "STUB: MT4_ZMQ_HOST not configured", request)

        message = json.dumps(request.__dict__)
        ctx = zmq.Context()
        sock = ctx.socket(zmq.PUSH)
        endpoint = f"tcp://{host}:{port}"
        try:
            sock.connect(endpoint)
            sock.send_string(message)
            return OrderResult(True, f"Sent to {endpoint}", request)
        finally:
            sock.disconnect(endpoint)
            sock.close(0)
            ctx.term()

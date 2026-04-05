from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from scaffold.runtime import get_runtime


class RemoteRuntimeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        payload = json.loads(body.decode("utf-8"))
        command = payload.get("command", "")
        args = payload.get("args", {})
        try:
            result = get_runtime().dispatch(command, args)
            out = {"result": result, "ok": True}
            code = 200
        except Exception as exc:
            out = {"result": str(exc), "ok": False}
            code = 500

        data = json.dumps(out).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_remote_mode(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = HTTPServer((host, port), RemoteRuntimeHandler)
    server.serve_forever()


def run_ssh_mode(host: str, user: str, command: str) -> str:
    return f"STUB: SSH mode not implemented for {user}@{host} ({command})"


def run_teleport_mode(cluster: str, command: str) -> str:
    return f"STUB: Teleport mode not implemented for {cluster} ({command})"

from __future__ import annotations

import json
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

from scaffold.runtime import get_runtime


class RemoteRuntimeHandler(BaseHTTPRequestHandler):
    """HTTP handler exposing runtime command dispatch over POST."""

    def do_POST(self) -> None:
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
    """Start blocking HTTP runtime server."""
    server = HTTPServer((host, port), RemoteRuntimeHandler)
    server.serve_forever()


def run_ssh_mode(host: str, user: str, command: str) -> str:
    """Execute command over SSH and return captured output."""
    if not shutil.which("ssh"):
        return "SSH client unavailable on this host"
    proc = subprocess.run(
        ["ssh", f"{user}@{host}", command],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()


def run_teleport_mode(cluster: str, command: str) -> str:
    """Execute command through Teleport tsh when available."""
    if not shutil.which("tsh"):
        return "Teleport client (tsh) unavailable on this host"
    proc = subprocess.run(
        ["tsh", "ssh", f"root@{cluster}", command],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()

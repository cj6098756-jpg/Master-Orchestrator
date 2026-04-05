from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class KAIROSTask:
    """Queued KAIROS daemon task."""

    task_id: str
    description: str
    priority: int
    status: str
    created_at: datetime
    result: str | None = None


class KAIROSDaemon:
    """Background priority queue for asynchronous system tasks."""

    def __init__(self) -> None:
        self.task_queue: list[KAIROSTask] = []
        self.running = False
        self._thread: threading.Thread | None = None

    def enqueue(self, description: str, priority: int = 5) -> KAIROSTask:
        task = KAIROSTask(str(uuid.uuid4()), description, priority, "PENDING", datetime.now(timezone.utc))
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority)
        return task

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self.running:
            pending = next((t for t in self.task_queue if t.status == "PENDING"), None)
            if pending:
                pending.status = "RUNNING"
                self._process_task(pending)
            time.sleep(30)

    def stop(self) -> None:
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=1)

    def _process_task(self, task: KAIROSTask) -> None:
        """Process queue item with deterministic execution outcome."""
        time.sleep(0.01)
        task.status = "DONE"
        task.result = f"Processed task '{task.description}' at {datetime.now(timezone.utc).isoformat()}"

    def status_report(self) -> str:
        return "\n".join(f"{t.task_id[:8]} | {t.status:8s} | {t.description}" for t in self.task_queue) or "Queue empty"

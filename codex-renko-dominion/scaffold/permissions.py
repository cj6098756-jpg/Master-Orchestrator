from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

DENY_PATTERNS = [
    "rm -rf", "os.system", "subprocess", "exec(", "eval(",
    "__import__", "open(", "shutil.rmtree", "drop table",
    "delete from", "format c:", "> /dev/", "curl | bash",
]

ALLOW_LIST = [
    "python main.py", "pytest", "pip install",
    "fct", "hurst", "backtest", "wfo", "monte-carlo",
    "lot-ladder", "doctrine", "renko", "dashboard",
    "kairos", "session", "history", "mwp-run", "crt",
]


@dataclass(frozen=True)
class PermissionAudit:
    timestamp: str
    action: str
    allowed: bool
    reason: str


AUDIT_LOG: list[PermissionAudit] = []


def check_permission(action: str) -> tuple[bool, str]:
    text = action.lower()
    for pattern in DENY_PATTERNS:
        if pattern in text:
            reason = f"Denied by pattern: {pattern}"
            AUDIT_LOG.append(PermissionAudit(datetime.now(timezone.utc).isoformat(), action, False, reason))
            return False, reason

    if not any(allowed in text for allowed in ALLOW_LIST):
        reason = "Denied: not in allow list"
        AUDIT_LOG.append(PermissionAudit(datetime.now(timezone.utc).isoformat(), action, False, reason))
        return False, reason

    reason = "Allowed"
    AUDIT_LOG.append(PermissionAudit(datetime.now(timezone.utc).isoformat(), action, True, reason))
    return True, reason


def get_audit_log() -> list[PermissionAudit]:
    return list(AUDIT_LOG)

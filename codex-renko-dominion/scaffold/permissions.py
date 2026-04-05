from __future__ import annotations

from dataclasses import dataclass

from scaffold.contracts import PermissionDecision, PermissionRequest, PermissionType, utc_now_iso

DENY_PATTERNS = [
    "rm -rf",
    "os.system",
    "subprocess",
    "exec(",
    "eval(",
    "__import__",
    "open(",
    "shutil.rmtree",
    "drop table",
    "delete from",
    "format c:",
    "> /dev/",
    "curl | bash",
]

ALLOW_LIST = [
    "python main.py",
    "pytest",
    "pip install",
    "fct",
    "hurst",
    "backtest",
    "wfo",
    "monte-carlo",
    "lot-ladder",
    "doctrine",
    "renko",
    "dashboard",
    "kairos",
    "session",
    "history",
    "mwp-run",
    "crt",
]


@dataclass(frozen=True)
class PermissionAudit:
    timestamp: str
    action: str
    allowed: bool
    reason: str
    permission_type: PermissionType


AUDIT_LOG: list[PermissionAudit] = []


def evaluate(request: PermissionRequest) -> PermissionDecision:
    """Centralized policy engine for all mutating paths."""
    text = request.action.lower()

    for pattern in DENY_PATTERNS:
        if pattern in text:
            decision = PermissionDecision(False, f"Denied by pattern: {pattern}", request)
            AUDIT_LOG.append(PermissionAudit(utc_now_iso(), request.action, False, decision.reason, request.permission_type))
            return decision

    if request.permission_type == PermissionType.READ:
        decision = PermissionDecision(True, "Allowed read-only operation", request)
        AUDIT_LOG.append(PermissionAudit(utc_now_iso(), request.action, True, decision.reason, request.permission_type))
        return decision

    if not any(allowed in text for allowed in ALLOW_LIST):
        decision = PermissionDecision(False, "Denied: not in allow list", request)
        AUDIT_LOG.append(PermissionAudit(utc_now_iso(), request.action, False, decision.reason, request.permission_type))
        return decision

    decision = PermissionDecision(True, "Allowed by policy", request)
    AUDIT_LOG.append(PermissionAudit(utc_now_iso(), request.action, True, decision.reason, request.permission_type))
    return decision


def check_permission(action: str) -> tuple[bool, str]:
    """Backward-compatible adapter for legacy callers."""
    decision = evaluate(PermissionRequest(actor="legacy", action=action, permission_type=PermissionType.EXECUTE))
    return decision.allowed, decision.reason


def get_audit_log() -> list[PermissionAudit]:
    return list(AUDIT_LOG)

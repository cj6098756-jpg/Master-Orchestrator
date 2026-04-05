from __future__ import annotations

from dataclasses import dataclass

MIN_ENTROPY = 0.50
MIN_OFI = 0.333


@dataclass(frozen=True)
class GateResult:
    """Result of two-factor entropy gate."""

    open: bool
    entropy: float
    ofi: float
    entropy_ok: bool
    ofi_ok: bool


def check_entropy_gate(entropy: float, ofi: float) -> GateResult:
    """Check minimum entropy and OFI thresholds."""
    entropy_ok = entropy >= MIN_ENTROPY
    ofi_ok = abs(ofi) >= MIN_OFI
    return GateResult(open=entropy_ok and ofi_ok, entropy=entropy, ofi=ofi, entropy_ok=entropy_ok, ofi_ok=ofi_ok)

from __future__ import annotations

from execution.entropy_gate import check_entropy_gate


def test_open_when_both_conditions_met():
    assert check_entropy_gate(0.5, 0.333).open


def test_closed_when_entropy_low():
    assert not check_entropy_gate(0.49, 0.4).open


def test_closed_when_ofi_low():
    assert not check_entropy_gate(0.8, 0.2).open


def test_both_conditions_required():
    r = check_entropy_gate(0.8, 0.1)
    assert (not r.open) and r.entropy_ok and (not r.ofi_ok)

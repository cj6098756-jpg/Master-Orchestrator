from __future__ import annotations

from codex.doctrine import check_doctrine
from codex.fct import FCTInputs, score_fct


def test_d001_increase_after_loss():
    assert not check_doctrine("increase position after loss").allowed


def test_d003_override_hurst():
    r = check_doctrine("override hurst breaker")
    assert (not r.allowed) and r.rule_id == "D003"


def test_a001_fct_grade_allowed():
    fct = score_fct(FCTInputs(*([0.9] * 7)))
    assert check_doctrine("enter on fct grade a", fct).allowed


def test_d002_when_none_fct():
    r = check_doctrine("enter trade")
    assert (not r.allowed) and r.rule_id == "D002"

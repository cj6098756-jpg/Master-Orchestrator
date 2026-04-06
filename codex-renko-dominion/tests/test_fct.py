from __future__ import annotations

from codex.fct import FCT_WEIGHTS, FCTInputs, score_fct


def test_weight_sum_one():
    assert abs(sum(FCT_WEIGHTS.values()) - 1.0) < 1e-9


def test_grade_boundaries():
    assert score_fct(FCTInputs(*([0.8] * 7))).grade == "A"
    assert score_fct(FCTInputs(*([0.65] * 7))).grade == "B"
    assert score_fct(FCTInputs(*([0.50] * 7))).grade == "C"
    assert score_fct(FCTInputs(*([0.35] * 7))).grade == "D"
    assert score_fct(FCTInputs(*([0.1] * 7))).grade == "F"


def test_tradeable_only_ab():
    assert score_fct(FCTInputs(*([0.9] * 7))).is_tradeable()
    assert score_fct(FCTInputs(*([0.7] * 7))).is_tradeable()
    assert not score_fct(FCTInputs(*([0.5] * 7))).is_tradeable()


def test_score_correctness():
    inp = FCTInputs(1, 0, 0, 0, 0, 0, 0)
    assert abs(score_fct(inp).value - 0.20) < 1e-9

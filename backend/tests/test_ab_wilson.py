from app.utils.stats import preference_decision, wilson_interval


def test_wilson_interval_all_wins():
    lo, hi = wilson_interval(100, 100)
    assert lo <= 1.0 and hi <= 1.0
    assert lo > 0.5


def test_wilson_interval_empty():
    lo, hi = wilson_interval(0, 0)
    assert (lo, hi) == (0.0, 1.0)


def test_preference_decision_clear_a():
    d = preference_decision(80, 100, epsilon=0.02)
    assert d["winner"] in ("a", "inconclusive")


def test_preference_decision_clear_b():
    d = preference_decision(0, 50, epsilon=0.02)
    assert d["winner"] in ("b", "inconclusive")

"""Small-sample statistics for A/B preference testing."""

from __future__ import annotations

import math


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for binomial proportion (wins / n). Returns (low, high)."""
    if n <= 0:
        return (0.0, 1.0)
    p = wins / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    inner = (p * (1 - p)) / n + z2 / (4 * n * n)
    margin = (z * math.sqrt(max(inner, 0.0))) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def preference_decision(
    wins_a: int, n: int, epsilon: float = 0.02, z: float = 1.96
) -> dict:
    """
    Simple policy: prefer A if lower Wilson bound > 0.5 + epsilon/2 style threshold,
    prefer B if upper Wilson bound < 0.5 - epsilon, else inconclusive.
    """
    if n <= 0:
        return {
            "winner": "none",
            "p_hat": None,
            "wilson_low": None,
            "wilson_high": None,
            "n": 0,
        }
    p_hat = wins_a / n
    lo, hi = wilson_interval(wins_a, n, z=z)
    half_eps = epsilon / 2
    if lo > 0.5 + half_eps:
        winner = "a"
    elif hi < 0.5 - half_eps:
        winner = "b"
    else:
        winner = "inconclusive"
    return {"winner": winner, "p_hat": p_hat, "wilson_low": lo, "wilson_high": hi, "n": n}

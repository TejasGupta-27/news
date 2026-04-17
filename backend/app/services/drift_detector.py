from collections import Counter

from scipy import stats
from river.drift import PageHinkley

from app.config import settings

REFERENCE_DISTRIBUTION = {
    "World": 0.25,
    "Sports": 0.25,
    "Business": 0.25,
    "Technology": 0.25,
}


def check_label_drift(
    predicted_labels: list[str],
    reference: dict[str, float] | None = None,
) -> tuple[float, bool]:
    if len(predicted_labels) < 30:
        return 1.0, False

    ref = reference or REFERENCE_DISTRIBUTION
    counts = Counter(predicted_labels)
    total = sum(counts.values())

    observed = [counts.get(name, 0) for name in settings.label_names]
    expected = [ref.get(name, 0.25) * total for name in settings.label_names]

    stat, p_value = stats.chisquare(observed, expected)
    drift_detected = p_value < settings.drift_pvalue_threshold
    return float(p_value), drift_detected


def check_confidence_drift(confidences: list[float]) -> tuple[float, bool]:
    if len(confidences) < 30:
        return 0.0, False

    ph = PageHinkley(min_instances=25, delta=0.005, threshold=50, alpha=0.9999)
    drift_score = 0.0

    for val in confidences:
        ph.update(val)
        if ph.drift_detected:
            drift_score = 1.0
            return drift_score, True

    return drift_score, False


def compute_current_distribution(predicted_names: list[str]) -> dict[str, float]:
    total = len(predicted_names)
    if total == 0:
        return {name: 0.0 for name in settings.label_names}
    counts = Counter(predicted_names)
    return {name: counts.get(name, 0) / total for name in settings.label_names}

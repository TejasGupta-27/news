from prometheus_client import Counter, Gauge, Histogram


prediction_total = Counter(
    "ainews_predictions_total",
    "Total predictions served",
    ["label", "model_version"],
)

prediction_latency = Histogram(
    "ainews_prediction_latency_seconds",
    "Prediction latency (model.predict only)",
    ["model_version"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

prediction_confidence = Histogram(
    "ainews_prediction_confidence",
    "Confidence of each prediction",
    ["model_version"],
    buckets=(0.25, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
)

cache_hits = Counter("ainews_cache_hits_total", "Prediction cache hits")
cache_misses = Counter("ainews_cache_misses_total", "Prediction cache misses")

drift_label_pvalue = Gauge(
    "ainews_drift_label_pvalue",
    "Most recent label-drift chi-square p-value",
    ["model_version"],
)
drift_confidence_score = Gauge(
    "ainews_drift_confidence_score",
    "Most recent confidence-drift score (PageHinkley)",
    ["model_version"],
)
drift_detected = Gauge(
    "ainews_drift_detected",
    "1 if last drift check fired (label or confidence), else 0",
    ["model_version"],
)
drift_checks_total = Counter(
    "ainews_drift_checks_total",
    "Number of drift checks run",
    ["outcome", "model_version"],
)

retrain_runs_total = Counter(
    "ainews_retrain_runs_total",
    "Retraining runs by final status",
    ["status", "trigger"],
)
model_f1_macro = Gauge(
    "ainews_model_f1_macro",
    "F1 (macro) of the currently-deployed model",
    ["model_version"],
)
model_accuracy = Gauge(
    "ainews_model_accuracy",
    "Accuracy of the currently-deployed model",
    ["model_version"],
)
model_info = Gauge(
    "ainews_model_info",
    "Current model version (label-only; value is always 1)",
    ["version"],
)


def set_model_info(version: str):
    model_info.clear()
    model_info.labels(version=version).set(1)


def set_model_scores(version: str, f1_macro: float, accuracy: float):
    model_f1_macro.clear()
    model_accuracy.clear()
    model_f1_macro.labels(model_version=version).set(f1_macro)
    model_accuracy.labels(model_version=version).set(accuracy)

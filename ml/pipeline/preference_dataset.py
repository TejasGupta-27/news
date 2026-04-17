"""
Pairwise preference training data from real user feedback only.

Load exports from GET /api/ab/export (JSON array or JSONL). Labels are the
recorded human choices (chose_model_a), not dataset-derived proxies.
"""

from __future__ import annotations

import json
from pathlib import Path

from datasets import Dataset


def prediction_to_summary(pred: dict) -> str:
    """Compact string for the preference model's second segment."""
    probs = pred.get("probabilities") or {}
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:4]
    prob_s = ", ".join(f"{k}:{v:.3f}" for k, v in top)
    return f"{pred.get('label', '?')} conf={float(pred.get('confidence', 0)):.3f} [{prob_s}]"


def load_pairwise_feedback_file(path: str | Path) -> Dataset:
    """Load from JSON array (GET /api/ab/export) or JSONL (one object per line)."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("Empty file")
    if raw.startswith("["):
        rows = json.loads(raw)
    else:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    texts, sa, sb, labels = [], [], [], []
    for row in rows:
        if row.get("chose_model_a") is None:
            continue
        texts.append(row["text"])
        sa.append(prediction_to_summary(row["prediction_a"]))
        sb.append(prediction_to_summary(row["prediction_b"]))
        labels.append(1 if row["chose_model_a"] else 0)
    if not texts:
        raise ValueError("No completed comparisons in file")
    return Dataset.from_dict({"text": texts, "summary_a": sa, "summary_b": sb, "label": labels})

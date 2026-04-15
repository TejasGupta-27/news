import argparse
import asyncio
import hashlib
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.db import async_session
from app.models.prediction import PredictionLog


BIASED_TEXTS = {
    "Sports": [
        "The team won the championship after an incredible comeback in the final quarter.",
        "She broke the world record at the Olympic finals last night.",
        "The coach announced a new lineup ahead of Sunday's match.",
        "Star striker signed a five-year contract extension with the club.",
        "The tournament will feature sixteen teams competing for the trophy.",
    ],
    "Business": [
        "The central bank raised interest rates by a quarter point.",
        "Shares of the tech giant surged after strong quarterly earnings.",
        "Oil prices climbed amid tight supply forecasts.",
    ],
}


def _fake_probs(dominant: str, confidence: float) -> dict[str, float]:
    labels = settings.label_names
    remaining = (1.0 - confidence) / (len(labels) - 1)
    return {lbl: (confidence if lbl == dominant else remaining) for lbl in labels}


async def insert_biased(count: int, dominant: str, confidence: float, low_confidence: bool):
    if dominant not in settings.label_names:
        raise ValueError(f"dominant must be one of {settings.label_names}")

    label_id = settings.label_names.index(dominant)
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        for i in range(count):
            text = random.choice(BIASED_TEXTS.get(dominant, BIASED_TEXTS["Sports"]))
            text = f"{text} [{uuid.uuid4().hex[:8]}]"
            conf = random.uniform(0.4, 0.6) if low_confidence else confidence
            log = PredictionLog(
                text=text,
                text_hash=hashlib.sha256(text.encode()).hexdigest(),
                predicted_label=label_id,
                predicted_name=dominant,
                confidence=conf,
                probabilities=_fake_probs(dominant, conf),
                explanation=None,
                model_version="simulated",
                created_at=now - timedelta(seconds=count - i),
            )
            db.add(log)
        await db.commit()
    print(f"Inserted {count} biased predictions (dominant={dominant}, low_confidence={low_confidence})")


async def run_drift_check():
    from app.workers.drift_worker import run_drift_check as _check
    report = await _check()
    if not report:
        print("No drift report produced (not enough samples).")
        return
    print("\n=== Drift Report ===")
    print(f"samples:             {report.sample_count}")
    print(f"label p-value:       {report.label_drift_pvalue:.6f}")
    print(f"label drift:         {report.label_drift_detected}")
    print(f"confidence drift:    {report.confidence_drift_detected} (score={report.confidence_drift_score})")
    print(f"current dist:        {report.current_distribution}")
    print(f"triggered retrain:   {report.triggered_retraining}")


def main():
    parser = argparse.ArgumentParser(description="Simulate distribution drift in the prediction log")
    parser.add_argument("--count", type=int, default=200, help="Number of biased predictions to insert")
    parser.add_argument("--dominant", default="Sports", help="Class to over-represent")
    parser.add_argument("--confidence", type=float, default=0.92)
    parser.add_argument("--low-confidence", action="store_true",
                        help="Use 0.4-0.6 confidences to trigger confidence (PageHinkley) drift")
    parser.add_argument("--no-check", action="store_true", help="Skip the drift check after inserting")
    args = parser.parse_args()

    async def _run():
        await insert_biased(args.count, args.dominant, args.confidence, args.low_confidence)
        if not args.no_check:
            await run_drift_check()

    asyncio.run(_run())


if __name__ == "__main__":
    main()

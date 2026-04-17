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
    "World": [
        "The United Nations Security Council convened an emergency session on the humanitarian crisis.",
        "Diplomats from twelve countries gathered in Geneva to discuss the peace accord.",
        "Protests erupted in the capital following the contested election results.",
        "The prime minister announced new sanctions targeting foreign officials.",
    ],
    "Technology": [
        "Researchers unveiled a breakthrough in quantum computing at the conference.",
        "The startup released an open-source framework for distributed machine learning.",
        "A newly disclosed zero-day vulnerability prompted an urgent security patch.",
        "The chip company launched its next-generation GPU with record bandwidth.",
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
            conf = (
                random.uniform(0.4, 0.6)
                if low_confidence
                else max(0.5, min(0.99, random.gauss(confidence, 0.03)))
            )
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
    api_url = os.environ.get("API_URL", "http://backend:8000")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{api_url}/api/drift/check")
            resp.raise_for_status()
            report = resp.json()
    except Exception as e:
        print(f"API drift check failed ({e}); running in-process (metrics won't update)")
        from app.workers.drift_worker import run_drift_check as _check
        r = await _check()
        if not r:
            print("No drift report produced (not enough samples).")
            return
        report = {
            "sample_count": r.sample_count,
            "label_drift_pvalue": r.label_drift_pvalue,
            "label_drift_detected": r.label_drift_detected,
            "confidence_drift_score": r.confidence_drift_score,
            "confidence_drift_detected": r.confidence_drift_detected,
            "current_distribution": r.current_distribution,
            "triggered_retraining": r.triggered_retraining,
        }

    if not report:
        print("No drift report produced (not enough samples).")
        return
    print("\n=== Drift Report ===")
    print(f"samples:             {report['sample_count']}")
    print(f"label p-value:       {report['label_drift_pvalue']:.6e}")
    print(f"label drift:         {report['label_drift_detected']}")
    print(f"confidence drift:    {report['confidence_drift_detected']} (score={report['confidence_drift_score']})")
    print(f"current dist:        {report['current_distribution']}")
    print(f"triggered retrain:   {report['triggered_retraining']}")


async def simulate_user_feedback(count: int, wrong_rate: float, api_url: str):
    import httpx

    label_names = settings.label_names
    n_labels = len(label_names)
    inserted = 0
    corrected = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        for _ in range(count):
            true_label_name = random.choice(label_names)
            base = random.choice(BIASED_TEXTS[true_label_name])
            text = f"{base} [{uuid.uuid4().hex[:6]}]"

            resp = await client.post(f"{api_url}/api/predict", json={"text": text})
            if resp.status_code != 200:
                print(f"predict failed: {resp.status_code} {resp.text[:120]}")
                continue
            body = resp.json()
            pid = body.get("prediction_id")
            predicted = body["label"]
            inserted += 1

            should_be_wrong = random.random() < wrong_rate
            if should_be_wrong and predicted == true_label_name:
                other_ids = [i for i, n in enumerate(label_names) if n != true_label_name]
                correct_id = random.choice(other_ids)
            else:
                correct_id = label_names.index(true_label_name)

            if pid:
                cresp = await client.patch(
                    f"{api_url}/api/predictions/{pid}/correct",
                    json={"corrected_label": correct_id},
                )
                if cresp.status_code == 200:
                    corrected += 1

    print(
        f"Feedback simulation: issued {inserted} /predict calls, submitted {corrected} corrections "
        f"({int(wrong_rate*100)}% intended wrong-rate)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Simulate distribution drift and/or user feedback to exercise the retrain pipeline"
    )
    sub = parser.add_subparsers(dest="mode", required=False)

    drift = sub.add_parser("drift", help="Inject biased PredictionLog rows (default mode)")
    drift.add_argument("--count", type=int, default=200)
    drift.add_argument("--dominant", default="Sports")
    drift.add_argument("--confidence", type=float, default=0.92)
    drift.add_argument("--low-confidence", action="store_true")
    drift.add_argument("--no-check", action="store_true")

    fb = sub.add_parser("feedback", help="Simulate users correcting predictions via the API")
    fb.add_argument("--count", type=int, default=40)
    fb.add_argument("--wrong-rate", type=float, default=0.4,
                    help="Fraction of corrections that disagree with the prediction (0-1)")
    fb.add_argument("--api-url", default=os.environ.get("API_URL", "http://backend:8000"))

    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--dominant", default="Sports")
    parser.add_argument("--confidence", type=float, default=0.92)
    parser.add_argument("--low-confidence", action="store_true")
    parser.add_argument("--no-check", action="store_true")
    args = parser.parse_args()

    async def _run():
        if args.mode == "feedback":
            await simulate_user_feedback(args.count, args.wrong_rate, args.api_url)
            return

        await insert_biased(args.count, args.dominant, args.confidence, args.low_confidence)
        if not args.no_check:
            await run_drift_check()

    asyncio.run(_run())


if __name__ == "__main__":
    main()

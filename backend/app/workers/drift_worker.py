import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import settings

_scheduler: BackgroundScheduler | None = None


def start_drift_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_drift_check_sync,
        "interval",
        minutes=settings.drift_check_interval_minutes,
        id="drift_check",
    )
    _scheduler.start()
    print(f"Drift scheduler started (interval: {settings.drift_check_interval_minutes}m)")


def stop_drift_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _run_drift_check_sync():
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run_drift_check())
    finally:
        loop.close()


async def run_drift_check():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.config import settings
    from app.models.prediction import PredictionLog
    from app.models.drift_report import DriftReport
    from app.services.drift_detector import (
        check_label_drift,
        check_confidence_drift,
        compute_current_distribution,
        REFERENCE_DISTRIBUTION,
    )

    engine = create_async_engine(settings.database_url, echo=False)
    local_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with local_session() as db:
        query = (
            select(PredictionLog)
            .order_by(PredictionLog.created_at.desc())
            .limit(settings.drift_window_size)
        )
        result = await db.execute(query)
        predictions = result.scalars().all()

        if len(predictions) < 30:
            print(f"Not enough predictions for drift check ({len(predictions)})")
            return None

        labels = [p.predicted_name for p in predictions]
        confidences = [p.confidence for p in predictions]

        label_pvalue, label_drift = check_label_drift(labels)
        conf_score, conf_drift = check_confidence_drift(confidences)
        current_dist = compute_current_distribution(labels)

        now = datetime.now(timezone.utc)
        window_end = predictions[0].created_at
        window_start = predictions[-1].created_at

        report = DriftReport(
            check_time=now,
            window_start=window_start,
            window_end=window_end,
            sample_count=len(predictions),
            label_drift_pvalue=label_pvalue,
            label_drift_detected=label_drift,
            confidence_drift_score=conf_score,
            confidence_drift_detected=conf_drift,
            reference_distribution=REFERENCE_DISTRIBUTION,
            current_distribution=current_dist,
            triggered_retraining=False,
        )

        if label_drift or conf_drift:
            print(f"Drift detected! Label p={label_pvalue:.4f}, Confidence drift={conf_drift}")
            report.triggered_retraining = True
            db.add(report)
            await db.commit()
        else:
            db.add(report)
            await db.commit()

    await engine.dispose()
    return report

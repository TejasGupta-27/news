import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import settings

_scheduler: BackgroundScheduler | None = None
_bg_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro):
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    def _log_err(t: asyncio.Task):
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            import traceback
            print(f"[bg task error] {exc!r}")
            traceback.print_exception(type(exc), exc, exc.__traceback__)

    task.add_done_callback(_log_err)
    return task


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
    from app.models.training_run import TrainingRun
    from app.services.drift_detector import (
        check_label_drift,
        check_confidence_drift,
        compute_current_distribution,
        REFERENCE_DISTRIBUTION,
    )

    engine = create_async_engine(settings.database_url, echo=False)
    local_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    latest_created_report = None

    async with local_session() as db:
        last_deploy_q = (
            select(TrainingRun)
            .where(TrainingRun.status == "completed", TrainingRun.deployed.is_(True))
            .order_by(TrainingRun.completed_at.desc())
            .limit(1)
        )
        last_deploy = (await db.execute(last_deploy_q)).scalar_one_or_none()
        since_deploy = last_deploy.completed_at if last_deploy else None

        running_q = select(TrainingRun).where(TrainingRun.status == "running").limit(1)
        running = (await db.execute(running_q)).scalar_one_or_none()
        if running:
            print(f"Retrain already running (started {running.started_at}); skipping drift check")
            await engine.dispose()
            return None

        # Get unique model versions
        model_versions_q = select(PredictionLog.model_version).distinct()
        if since_deploy is not None:
            model_versions_q = model_versions_q.where(PredictionLog.created_at > since_deploy)
        model_versions_result = await db.execute(model_versions_q)
        model_versions = [row[0] for row in model_versions_result.all() if row[0]]

        for model_version in model_versions:
            last_report_q = (
                select(DriftReport)
                .where(DriftReport.model_version == model_version)
                .order_by(DriftReport.check_time.desc())
                .limit(1)
            )
            last_report = (await db.execute(last_report_q)).scalar_one_or_none()
            if (
                last_report
                and (last_report.label_drift_detected or last_report.confidence_drift_detected)
                and (last_deploy is None or last_deploy.completed_at <= last_report.check_time)
            ):
                print(
                    f"Unresolved drift for model {model_version} at {last_report.check_time}; "
                    "suppressing duplicate report"
                )
                continue

            query = select(PredictionLog).where(PredictionLog.model_version == model_version).order_by(PredictionLog.created_at.desc())
            if since_deploy is not None:
                query = query.where(PredictionLog.created_at > since_deploy)
            query = query.limit(settings.drift_window_size)
            result = await db.execute(query)
            predictions = result.scalars().all()

            if len(predictions) < 30:
                continue

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
                model_version=model_version,
            )

            from app.utils import metrics as m
            m.drift_label_pvalue.set(label_pvalue)
            m.drift_confidence_score.set(conf_score)
            m.drift_detected.set(1 if (label_drift or conf_drift) else 0)
            m.drift_checks_total.labels(
                outcome="drift" if (label_drift or conf_drift) else "ok"
            ).inc()

            db.add(report)
            await db.commit()
            await db.refresh(report)
            latest_created_report = report

            if label_drift or conf_drift:
                print(f"Drift detected for model {model_version}! Label p={label_pvalue:.4f}, Confidence drift={conf_drift}")
                from app.services.retrainer import claim_retrain_slot, _execute_retrain
                reason = "label_drift" if label_drift else "confidence_drift"
                model_type = "B" if model_version.startswith("ab-b:") else "A"
                tr_id = await claim_retrain_slot(report.id, reason)
                if tr_id is not None:
                    _fire_and_forget(_execute_retrain(tr_id, reason, model_type))
                    report.triggered_retraining = True
                    print(f"[drift_worker] retrain claimed ({tr_id}, reason={reason}, model={model_type})")
                else:
                    report.triggered_retraining = False
                    print("[drift_worker] retrain slot not claimed (another run already active)")
                await db.commit()

    await engine.dispose()
    return latest_created_report

import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

_scheduler: BackgroundScheduler | None = None


def start_ab_feedback_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_ab_feedback_refresh_sync,
        "interval",
        minutes=settings.ab_feedback_refresh_interval_minutes,
        id="ab_feedback_refresh",
    )
    _scheduler.start()
    print(
        f"A/B feedback scheduler started (interval: {settings.ab_feedback_refresh_interval_minutes}m)"
    )


def stop_ab_feedback_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _run_ab_feedback_refresh_sync():
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run_ab_feedback_refresh())
    finally:
        loop.close()


async def run_ab_feedback_refresh():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import settings as app_settings
    from app.services.ab_routing import get_routing_state, refresh_routing_from_pairwise_feedback

    engine = create_async_engine(app_settings.database_url, echo=False)
    local_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with local_session() as db:
            state = await get_routing_state(db)
            if state is None or not state.ab_testing_enabled:
                return
            await refresh_routing_from_pairwise_feedback(db)
    finally:
        await engine.dispose()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.classifier import classifier_service
    from app.utils.metrics import set_model_info
    await classifier_service.load_model()
    set_model_info(classifier_service.model_version)

    from app.workers.drift_worker import start_drift_scheduler
    start_drift_scheduler()

    yield

    from app.workers.drift_worker import stop_drift_scheduler
    stop_drift_scheduler()


app = FastAPI(title="AI-News Monitor", version="0.1.0", lifespan=lifespan)

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics", "/api/health"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import predict, drift, training, health  # noqa: E402

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(predict.router, prefix="/api", tags=["predictions"])
app.include_router(drift.router, prefix="/api", tags=["drift"])
app.include_router(training.router, prefix="/api", tags=["training"])

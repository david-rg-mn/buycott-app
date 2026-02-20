from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import SessionLocal
from .routes.search import router as search_router
from .schemas import HealthMetricsResponse, HealthResponse
from .telemetry.logging_utils import configure_logging
from .telemetry.middleware import TelemetryMiddleware
from .telemetry.repository import fetch_average_latency_metrics

configure_logging(settings.log_level, settings.perf_log_level)
app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TelemetryMiddleware)

app.include_router(search_router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return HealthResponse(status="ok")


@app.get("/health/metrics", response_model=HealthMetricsResponse)
def health_metrics() -> HealthMetricsResponse:
    with SessionLocal() as session:
        metrics = fetch_average_latency_metrics(session)
    return HealthMetricsResponse(**metrics)

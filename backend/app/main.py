from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import SessionLocal
from .routes.search import router as search_router
from .schemas import HealthResponse

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return HealthResponse(status="ok")

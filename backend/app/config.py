from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Buycott API"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "postgresql+psycopg://buycott:buycott@localhost:5432/buycott"

    embedding_dimension: int = 384
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    enable_model_embeddings: bool = True

    max_ontology_depth: int = 4
    top_k_per_vector: int = 40
    search_result_limit: int = 20
    min_similarity: float = 0.30
    max_search_distance_km: float = 120.0

    walking_threshold_minutes: int = 15
    default_timezone: str = "America/Chicago"

    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "BUYCOTT_LOG_LEVEL"))
    perf_log_level: str = Field(
        default="PERF",
        validation_alias=AliasChoices("PERF_LOG_LEVEL", "BUYCOTT_PERF_LOG_LEVEL"),
    )
    telemetry_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("TELEMETRY_ENABLED", "BUYCOTT_TELEMETRY_ENABLED"),
    )

    @field_validator("log_level", "perf_log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"DEBUG", "INFO", "PERF", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported log level")
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

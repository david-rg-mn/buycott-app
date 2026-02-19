from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="BUYCOTT_", extra="ignore")

    app_name: str = "Buycott API"
    app_env: str = "dev"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg://buycott:buycott@localhost:5432/buycott"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"
    embedding_dimension: int = 384
    embedding_batch_size: int = 32
    embedding_normalize: bool = True

    ontology_min_depth: int = 3
    ontology_max_depth: int = 5

    local_only_default: bool = True
    walking_threshold_minutes_default: int = 15
    driving_kmh_default: float = 30.0
    walking_kmh_default: float = 5.0

    mapbox_token: str | None = None
    google_distance_matrix_key: str | None = None

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

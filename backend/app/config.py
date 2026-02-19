from functools import lru_cache

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
    min_similarity: float = 0.15

    walking_threshold_minutes: int = 15
    default_timezone: str = "America/Chicago"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

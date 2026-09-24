"""Application settings.

Every external dependency (Postgres, Redis, Qdrant, Neo4j, LLM providers) is optional
at runtime: when a service is not configured the application falls back to a local,
deterministic implementation so the product stays runnable end-to-end.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # --- App -------------------------------------------------------------
    app_name: str = "PathFinder AI"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Security --------------------------------------------------------
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_secure: bool = False
    encryption_key: str | None = None  # Fernet key; derived from secret_key if absent

    google_client_id: str | None = None
    google_client_secret: str | None = None
    oauth_redirect_url: str = "http://localhost:3000/api/v1/auth/oauth/google/callback"

    # --- Data stores -------------------------------------------------------
    database_url: str = f"sqlite:///{BASE_DIR / 'pathfinder.db'}"
    redis_url: str | None = None
    qdrant_url: str | None = None  # e.g. http://qdrant:6333 ; None -> embedded in-memory Qdrant
    qdrant_api_key: str | None = None
    qdrant_collection: str = "pathfinder_knowledge"
    neo4j_uri: str | None = None  # e.g. bolt://neo4j:7687 ; None -> in-memory graph
    neo4j_user: str = "neo4j"
    neo4j_password: str = "pathfinder"

    # --- AI ----------------------------------------------------------------
    llm_provider: Literal["auto", "openai", "gemini", "none"] = "auto"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    embedding_provider: Literal["auto", "openai", "huggingface", "hash"] = "auto"
    hf_embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str | None = None  # e.g. cross-encoder/ms-marco-MiniLM-L-6-v2
    llm_timeout_seconds: float = 45.0

    # --- Background jobs ----------------------------------------------------
    celery_broker_url: str | None = None  # defaults to redis_url
    celery_eager: bool = True  # run tasks inline when no worker/broker is available

    # --- Uploads -------------------------------------------------------------
    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_mb: int = 8
    keep_uploaded_files: bool = True  # False -> delete file after extraction

    # --- Rate limits -----------------------------------------------------------
    rate_limit_ai_per_minute: int = 20
    rate_limit_auth_per_minute: int = 10

    # --- Observability ---------------------------------------------------------
    otel_exporter_otlp_endpoint: str | None = None
    langsmith_api_key: str | None = None
    langsmith_project: str = "pathfinder-ai"

    data_dir: Path = BASE_DIR / "data"
    seed_demo_user: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def fernet_key(self) -> bytes:
        if self.encryption_key:
            return self.encryption_key.encode()
        digest = hashlib.sha256(("pathfinder-fernet:" + self.secret_key).encode()).digest()
        return base64.urlsafe_b64encode(digest)

    @property
    def resolved_llm_provider(self) -> str:
        if self.llm_provider != "auto":
            if self.llm_provider == "openai" and not self.openai_api_key:
                return "none"
            if self.llm_provider == "gemini" and not self.gemini_api_key:
                return "none"
            return self.llm_provider
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"
        return "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()

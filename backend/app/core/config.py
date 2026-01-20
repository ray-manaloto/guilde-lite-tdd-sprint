"""Application configuration using Pydantic BaseSettings."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from pathlib import Path
from typing import Literal

from pydantic import computed_field, field_validator, model_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    for path in [current, current.parent]:
        env_file = path / ".env"
        if env_file.exists():
            return env_file
    return None


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )

    # === Project ===
    PROJECT_NAME: str = "guilde_lite_tdd_sprint"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "local", "staging", "production"] = "local"

    # === Logfire ===
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_SERVICE_NAME: str = "guilde_lite_tdd_sprint"
    LOGFIRE_ENVIRONMENT: str = "development"
    LOGFIRE_SEND_TO_LOGFIRE: bool | Literal["if-token-present"] = "if-token-present"
    LOGFIRE_TRACE_URL_TEMPLATE: str | None = None
    TELEMETRY_FILE: str | None = None

    @field_validator("LOGFIRE_SEND_TO_LOGFIRE", mode="before")
    @classmethod
    def normalize_logfire_send_to_logfire(cls, v: str | bool | None):
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"true", "1", "yes", "on", "always"}:
                return True
            if normalized in {"false", "0", "no", "off", "never"}:
                return False
            if normalized in {"if-token-present", "if_token_present"}:
                return "if-token-present"
        return v

    # === Database (PostgreSQL async) ===
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "guilde_lite_tdd_sprint"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build sync PostgreSQL connection URL (for Alembic)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Pool configuration
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # === Auth (SECRET_KEY for JWT/Session/Admin) ===
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate SECRET_KEY is secure in production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        # Get environment from values if available
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production-use-openssl-rand-hex-32" and env == "production":
            raise ValueError(
                "SECRET_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    # === JWT Settings ===
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # === OAuth2 (Google) ===
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/oauth/google/callback"

    # === Auth (API Key) ===
    API_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate API_KEY is set in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production" and env == "production":
            raise ValueError(
                "API_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """Build Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # === Rate Limiting ===
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # === Celery ===
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # === Sentry ===
    SENTRY_DSN: str | None = None

    # === Prometheus ===
    PROMETHEUS_METRICS_PATH: str = "/metrics"
    PROMETHEUS_INCLUDE_IN_SCHEMA: bool = False

    # === File Storage (S3/MinIO) ===
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "guilde_lite_tdd_sprint"
    S3_REGION: str = "us-east-1"

    # === AI Agent (pydantic_ai) ===
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = ""
    OPENAI_BASE_URL: str | None = None
    OPENAI_ORG: str | None = None
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = ""
    ANTHROPIC_BASE_URL: str | None = None
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = ""
    AI_MODEL: str = "gpt-4o-mini"
    AI_TEMPERATURE: float = 0.7
    JUDGE_MODEL: str = ""
    AI_FRAMEWORK: str = "pydantic_ai"
    LLM_PROVIDER: Literal["openai", "anthropic", "openrouter"] = "openai"
    PLANNING_INTERVIEW_MODE: Literal["live", "stub"] = "live"
    AGENT_BROWSER_ENABLED: bool = True
    AGENT_BROWSER_TIMEOUT_SECONDS: int = 60
    HTTP_FETCH_ENABLED: bool = True
    HTTP_FETCH_TIMEOUT_SECONDS: int = 15
    HTTP_FETCH_MAX_CHARS: int = 12000
    DUAL_SUBAGENT_ENABLED: bool = True
    AGENT_FS_ENABLED: bool = True
    AUTOCODE_ARTIFACTS_DIR: Path | None = Path("/Users/ray.manaloto.guilde/dev/tmp/guilde-lite-tdd-sprint-filesystem")

    @model_validator(mode="after")
    def validate_llm_provider_settings(self):  # type: ignore[override]
        """Validate API keys and models for the configured LLM provider."""
        provider = self.LLM_PROVIDER.lower()
        if provider == "openai":
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY must be set when LLM_PROVIDER=openai")
            if not self.OPENAI_MODEL:
                raise ValueError("OPENAI_MODEL must be set when LLM_PROVIDER=openai")
            if not self.OPENAI_MODEL.startswith("openai-responses:"):
                raise ValueError("OPENAI_MODEL must start with 'openai-responses:' for OpenAI.")
        elif provider == "anthropic":
            if not self.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY must be set when LLM_PROVIDER=anthropic")
            if not self.ANTHROPIC_MODEL:
                raise ValueError("ANTHROPIC_MODEL must be set when LLM_PROVIDER=anthropic")
        elif provider == "openrouter":
            if not self.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY must be set when LLM_PROVIDER=openrouter")
            if not self.OPENROUTER_MODEL:
                raise ValueError("OPENROUTER_MODEL must be set when LLM_PROVIDER=openrouter")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def LLM_MODEL(self) -> str:
        """Select the active model for the configured provider."""
        return self.model_for_provider(self.LLM_PROVIDER)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def JUDGE_LLM_MODEL(self) -> str:
        """Select the judge model, falling back to the primary model."""
        return self.JUDGE_MODEL or self.LLM_MODEL

    def model_for_provider(self, provider: str) -> str:
        """Return the model name for a specific provider."""
        provider = provider.lower()
        if provider == "anthropic":
            return self.ANTHROPIC_MODEL or self.AI_MODEL
        if provider == "openrouter":
            return self.OPENROUTER_MODEL or self.AI_MODEL
        return self.OPENAI_MODEL or self.AI_MODEL

    def api_key_for_provider(self, provider: str) -> str:
        """Return the API key for a specific provider."""
        provider = provider.lower()
        if provider == "anthropic":
            return self.ANTHROPIC_API_KEY
        if provider == "openrouter":
            return self.OPENROUTER_API_KEY
        return self.OPENAI_API_KEY

    def validate_dual_subagent_settings(self) -> None:
        """Validate settings for the dual-subagent + judge workflow."""
        if not self.DUAL_SUBAGENT_ENABLED:
            return
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set for dual-subagent mode")
        if not self.OPENAI_MODEL:
            raise ValueError("OPENAI_MODEL must be set for dual-subagent mode")
        if not self.OPENAI_MODEL.startswith("openai-responses:"):
            raise ValueError("OPENAI_MODEL must start with 'openai-responses:' for OpenAI.")
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY must be set for dual-subagent mode")
        if not self.ANTHROPIC_MODEL:
            raise ValueError("ANTHROPIC_MODEL must be set for dual-subagent mode")
        if not self.JUDGE_MODEL:
            raise ValueError("JUDGE_MODEL must be set for dual-subagent mode")
        if not self.JUDGE_MODEL.startswith("openai-responses:"):
            raise ValueError("JUDGE_MODEL must start with 'openai-responses:' for OpenAI.")

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Warn if CORS_ORIGINS is too permissive in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if "*" in v and env == "production":
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' in production! Specify explicit allowed origins."
            )
        return v


settings = Settings()

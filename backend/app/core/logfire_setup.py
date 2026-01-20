"""Logfire observability configuration."""

import logfire

from app.core.config import settings


def setup_logfire() -> None:
    """Configure Logfire instrumentation."""
    config = {
        "service_name": settings.LOGFIRE_SERVICE_NAME,
        "environment": settings.LOGFIRE_ENVIRONMENT,
        "send_to_logfire": settings.LOGFIRE_SEND_TO_LOGFIRE,
    }
    if settings.LOGFIRE_TOKEN:
        config["token"] = settings.LOGFIRE_TOKEN

    logfire.configure(**config)


def instrument_app(app):
    """Instrument FastAPI app with Logfire."""
    logfire.instrument_fastapi(app)


def instrument_asyncpg():
    """Instrument asyncpg for PostgreSQL."""
    logfire.instrument_asyncpg()


def instrument_pydantic_ai():
    """Instrument PydanticAI for AI agent observability."""
    logfire.instrument_pydantic_ai()

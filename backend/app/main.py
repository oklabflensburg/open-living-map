import logging

from app.api.routes import health
from app.api.routes import compare, metadata, recommendations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import regions
from app.core.config import settings
from app.core.db import SchemaDriftError, assert_schema_is_current
from app.core.logging import configure_logging, request_logging_middleware

configure_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

app.middleware("http")(request_logging_middleware)


@app.on_event("startup")
def startup() -> None:
    """Fail fast if the database schema is behind the application model."""
    try:
        assert_schema_is_current()
    except SchemaDriftError:
        logger.exception("Startup aborted because the database schema is outdated.")
        raise
    logger.info("Schema checks passed.")


app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(regions.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
app.include_router(compare.router, prefix=settings.api_prefix)
app.include_router(metadata.router, prefix=settings.api_prefix)

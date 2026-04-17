from app.api.routes import health
from app.api.routes import compare, metadata, recommendations
from fastapi import FastAPI

from app.api.routes import regions
from app.core.config import settings
from app.core.db import ensure_region_schema_compatibility

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    ensure_region_schema_compatibility()

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(regions.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
app.include_router(compare.router, prefix=settings.api_prefix)
app.include_router(metadata.router, prefix=settings.api_prefix)

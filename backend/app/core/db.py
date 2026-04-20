import logging
from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.database_url, echo=False)
logger = logging.getLogger(__name__)


class SchemaDriftError(RuntimeError):
    """Raised when the database schema does not match the application model."""


def _get_column_names(table_name: str) -> set[str]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        logger.warning("Schema drift detected: table %s is missing.", table_name)
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def check_indicator_schema_drift() -> bool:
    """Check if indicator_definition table has expected columns.
    Returns True if schema matches expectations, False if drift detected."""
    column_names = _get_column_names("indicator_definition")
    
    expected_columns = {"normalization_mode"}
    missing = expected_columns - column_names
    
    if missing:
        logger.warning(
            f"Schema drift detected in indicator_definition: missing columns {missing}. "
            f"Run alembic migrations to fix."
        )
        return False
    return True


def check_score_schema_drift() -> bool:
    """Check if score-related tables have expected columns.
    Returns True if schema matches expectations, False if drift detected."""
    snapshot_names = _get_column_names("region_score_snapshot")
    pref_names = _get_column_names("user_preference_session")

    expected_snapshot = {
        "score_landuse",
        "coverage_climate",
        "coverage_air",
        "coverage_safety",
        "coverage_demographics",
        "coverage_amenities",
        "coverage_landuse",
        "coverage_oepnv",
    }
    expected_pref = {"landuse_weight", "created_at"}
    
    missing_snapshot = expected_snapshot - snapshot_names
    missing_pref = expected_pref - pref_names
    
    if missing_snapshot or missing_pref:
        logger.warning(
            f"Schema drift detected in score tables: "
            f"missing in snapshot {missing_snapshot}, "
            f"missing in preference {missing_pref}. "
            f"Run alembic migrations to fix."
        )
        return False
    return True


def check_region_schema_drift() -> bool:
    """Check if region table has expected columns.
    Returns True if schema matches expectations, False if drift detected."""
    column_names = _get_column_names("region")
    
    expected_columns = {"bem", "slug", "district_name", "wikidata_id", "wikidata_url", "wikipedia_url"}
    missing = expected_columns - column_names
    
    if missing:
        logger.warning(
            f"Schema drift detected in region: missing columns {missing}. "
            f"Run alembic migrations to fix."
        )
        return False
    
    # Check for empty slugs that need population
    with Session(engine) as session:
        rows = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM region
                WHERE slug IS NULL OR slug = ''
                """
            )
        ).scalar()
        
        if rows and rows > 0:
            logger.warning(
                f"Found {rows} regions with empty slugs. "
                f"Run data migration to populate slugs."
            )
    
    return True


def check_schema_drift() -> bool:
    """Check all schema expectations.
    Returns True if all checks pass, False if any drift detected."""
    indicator_ok = check_indicator_schema_drift()
    score_ok = check_score_schema_drift()
    region_ok = check_region_schema_drift()
    
    return indicator_ok and score_ok and region_ok


def assert_schema_is_current() -> None:
    if not check_schema_drift():
        raise SchemaDriftError(
            "Database schema drift detected. Run `alembic upgrade head` before starting the app or ETL."
        )


def get_session() -> Generator[Session, None, None]:
    """Get database session without performing any DDL operations."""
    with Session(engine) as session:
        yield session

import logging
from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.database_url, echo=False)
logger = logging.getLogger(__name__)


class SchemaDriftError(RuntimeError):
    """Raised when the database schema does not match the application model."""


def _get_column_names(table_name: str, schema: str | None = None) -> set[str]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names(schema=schema))
    if table_name not in table_names:
        qualified_name = f"{schema}.{table_name}" if schema else table_name
        logger.warning("Schema drift detected: table %s is missing.", qualified_name)
        return set()
    return {column["name"] for column in inspector.get_columns(table_name, schema=schema)}


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

    expected_columns = {
        "bem",
        "slug",
        "district_name",
        "wikidata_id",
        "wikidata_url",
        "wikipedia_url",
    }
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
                f"Found {rows} regions with empty slugs. Run data migration to populate slugs."
            )

    return True


def check_postal_schema_drift() -> bool:
    """Check if postal.region_postal_code has expected columns."""
    column_names = _get_column_names("region_postal_code", schema="postal")

    expected_columns = {
        "postal_code",
        "region_ars",
        "region_name",
        "postal_name",
        "overlap_area",
        "is_primary",
        "updated_at",
    }
    missing = expected_columns - column_names

    if missing:
        logger.warning(
            "Schema drift detected in postal.region_postal_code: missing columns %s. "
            "Run alembic migrations to fix.",
            missing,
        )
        return False
    return True


def check_etl_schema_drift() -> bool:
    """Check if ETL audit tables have expected columns."""
    run_columns = _get_column_names("etl_run")
    source_columns = _get_column_names("etl_run_source")

    expected_run_columns = {
        "job_name",
        "status",
        "rows_written",
        "error_message",
        "started_at",
        "finished_at",
    }
    expected_source_columns = {
        "etl_run_id",
        "source_name",
        "source_url",
        "source_version",
        "source_hash",
    }

    missing_run = expected_run_columns - run_columns
    missing_source = expected_source_columns - source_columns

    if missing_run or missing_source:
        logger.warning(
            "Schema drift detected in ETL audit tables: missing in etl_run %s, missing in etl_run_source %s. "
            "Run alembic migrations to fix.",
            missing_run,
            missing_source,
        )
        return False
    return True


def check_climate_schema_drift() -> bool:
    """Check if climate.region_climate_station has expected columns."""
    column_names = _get_column_names("region_climate_station", schema="climate")

    expected_columns = {
        "region_ars",
        "indicator_key",
        "station_id",
        "station_name",
        "latitude",
        "longitude",
        "source_url",
    }
    missing = expected_columns - column_names

    if missing:
        logger.warning(
            "Schema drift detected in climate.region_climate_station: missing columns %s. "
            "Run alembic migrations to fix.",
            missing,
        )
        return False
    return True


def check_schema_drift() -> bool:
    """Check all schema expectations.
    Returns True if all checks pass, False if any drift detected."""
    indicator_ok = check_indicator_schema_drift()
    score_ok = check_score_schema_drift()
    region_ok = check_region_schema_drift()
    postal_ok = check_postal_schema_drift()
    etl_ok = check_etl_schema_drift()
    climate_ok = check_climate_schema_drift()

    return indicator_ok and score_ok and region_ok and postal_ok and etl_ok and climate_ok


def assert_schema_is_current() -> None:
    if not check_schema_drift():
        raise SchemaDriftError(
            "Database schema drift detected. Run `alembic upgrade head` before starting the app or ETL."
        )


def get_session() -> Generator[Session, None, None]:
    """Get database session without performing any DDL operations."""
    with Session(engine) as session:
        yield session

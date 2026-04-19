from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, create_engine

from app.core.ars import slugify_region_name
from app.core.config import settings

engine = create_engine(settings.database_url, echo=False)


def ensure_indicator_schema_compatibility() -> None:
    with Session(engine) as session:
        session.execute(
            text(
                """
                ALTER TABLE indicator_definition
                ADD COLUMN IF NOT EXISTS normalization_mode text DEFAULT 'log' NOT NULL;
                """
            )
        )
        session.commit()


def ensure_score_schema_compatibility() -> None:
    with Session(engine) as session:
        session.execute(
            text(
                """
                ALTER TABLE region_score_snapshot
                ADD COLUMN IF NOT EXISTS score_landuse double precision DEFAULT 0 NOT NULL;
                """
            )
        )
        session.execute(
            text(
                """
                ALTER TABLE user_preference_session
                ADD COLUMN IF NOT EXISTS landuse_weight integer DEFAULT 0 NOT NULL;
                """
            )
        )
        session.commit()


def ensure_region_schema_compatibility() -> None:
    with Session(engine) as session:
        session.execute(
            text(
                """
                ALTER TABLE region
                ADD COLUMN IF NOT EXISTS slug text,
                ADD COLUMN IF NOT EXISTS district_name text,
                ADD COLUMN IF NOT EXISTS wikidata_id text,
                ADD COLUMN IF NOT EXISTS wikidata_url text,
                ADD COLUMN IF NOT EXISTS wikipedia_url text;
                """
            )
        )
        rows = session.execute(
            text(
                """
                SELECT id, name
                FROM region
                WHERE slug IS NULL OR slug = ''
                """
            )
        ).all()
        for row_id, name in rows:
            session.execute(
                text("UPDATE region SET slug = :slug WHERE id = :row_id"),
                {"slug": slugify_region_name(str(name)), "row_id": row_id},
            )
        session.commit()


def get_session() -> Generator[Session, None, None]:
    ensure_indicator_schema_compatibility()
    ensure_score_schema_compatibility()
    ensure_region_schema_compatibility()
    with Session(engine) as session:
        yield session

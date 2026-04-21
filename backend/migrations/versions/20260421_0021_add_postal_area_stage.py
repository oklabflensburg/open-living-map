"""add postal area stage table

Revision ID: 20260421_0021
Revises: 20260421_0020
Create Date: 2026-04-21 01:20:00
"""

from alembic import op


revision = "20260421_0021"
down_revision = "20260421_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS postal.postal_area_stage (
            source_id varchar NOT NULL,
            postal_code varchar(5) NOT NULL,
            postal_name varchar NULL,
            geom_raw geometry(Geometry, 3857) NOT NULL,
            geom geometry(MultiPolygon, 3857) NULL,
            updated_at timestamp without time zone NOT NULL,
            PRIMARY KEY (source_id)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_area_stage_postal_code
        ON postal.postal_area_stage (postal_code);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_area_stage_geom_raw_gist
        ON postal.postal_area_stage
        USING gist (geom_raw);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_area_stage_geom_gist
        ON postal.postal_area_stage
        USING gist (geom);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS postal.postal_area_stage;")

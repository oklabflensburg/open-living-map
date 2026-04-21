"""add climate station assignment table

Revision ID: 20260421_0023
Revises: 20260421_0022
Create Date: 2026-04-21 23:30:00
"""

from alembic import op


revision = "20260421_0023"
down_revision = "20260421_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS climate;")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS climate.region_climate_station (
            region_ars varchar NOT NULL,
            indicator_key varchar NOT NULL,
            station_id varchar NOT NULL,
            station_name varchar NOT NULL,
            latitude double precision NULL,
            longitude double precision NULL,
            source_url varchar NULL,
            PRIMARY KEY (region_ars, indicator_key)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_climate_station_region_ars
        ON climate.region_climate_station (region_ars);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS climate.region_climate_station;")

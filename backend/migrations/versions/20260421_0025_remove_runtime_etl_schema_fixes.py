"""remove runtime etl schema fixes

Revision ID: 20260421_0025
Revises: 20260421_0024
Create Date: 2026-04-21 06:20:00
"""

from alembic import op


revision = "20260421_0025"
down_revision = "20260421_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS osm.amenity_poi_stage
        ADD COLUMN IF NOT EXISTS name varchar NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS oepnv.gtfs_feed_registry
        ADD COLUMN IF NOT EXISTS schema_name text;
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS oepnv.gtfs_stage_registry
        ADD COLUMN IF NOT EXISTS active_stage_key text;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'traffic'
                  AND table_name = 'accident_point'
                  AND column_name = 'district_ars'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'traffic'
                  AND table_name = 'accident_point'
                  AND column_name = 'region_ars'
            ) THEN
                EXECUTE 'ALTER TABLE traffic.accident_point RENAME COLUMN district_ars TO region_ars';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS oepnv.gtfs_stage_registry
        DROP COLUMN IF EXISTS active_stage_key;
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS oepnv.gtfs_feed_registry
        DROP COLUMN IF EXISTS schema_name;
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS osm.amenity_poi_stage
        DROP COLUMN IF EXISTS name;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'traffic'
                  AND table_name = 'accident_point'
                  AND column_name = 'region_ars'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'traffic'
                  AND table_name = 'accident_point'
                  AND column_name = 'district_ars'
            ) THEN
                EXECUTE 'ALTER TABLE traffic.accident_point RENAME COLUMN region_ars TO district_ars';
            END IF;
        END
        $$;
        """
    )

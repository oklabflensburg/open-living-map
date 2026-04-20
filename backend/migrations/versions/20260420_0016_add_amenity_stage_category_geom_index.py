"""add category+geom gist index for amenity poi stage

Revision ID: 20260420_0016
Revises: 20260420_0015
Create Date: 2026-04-20 22:35:00
"""

from alembic import op


revision = "20260420_0016"
down_revision = "20260420_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('osm.amenity_poi_stage') IS NOT NULL THEN
                CREATE INDEX IF NOT EXISTS ix_osm_amenity_poi_stage_category_geom_gist
                ON osm.amenity_poi_stage
                USING gist (category, geom);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS osm.ix_osm_amenity_poi_stage_category_geom_gist;")
    op.execute("DROP INDEX IF EXISTS ix_osm_amenity_poi_stage_category_geom_gist;")

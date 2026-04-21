"""add spatial indexes for postal code ETL

Revision ID: 20260421_0020
Revises: 20260421_0019
Create Date: 2026-04-21 01:00:00
"""

from alembic import op


revision = "20260421_0020"
down_revision = "20260421_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_osm_planet_osm_polygon_postal_way_gist
        ON osm.planet_osm_polygon
        USING gist (way)
        WHERE way IS NOT NULL
          AND COALESCE("boundary", tags -> 'boundary') = 'postal_code';
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_geo_municipality_boundary_geom_3857_gist
        ON geo.municipality_boundary
        USING gist (ST_Transform(geom, 3857));
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS geo.ix_geo_municipality_boundary_geom_3857_gist;")
    op.execute("DROP INDEX IF EXISTS osm.ix_osm_planet_osm_polygon_postal_way_gist;")

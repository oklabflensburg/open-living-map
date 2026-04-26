"""initial

Revision ID: 20260413_0001
Revises:
Create Date: 2026-04-13 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260413_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS hstore")

    op.create_table(
        "region",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ars", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("state_code", sa.String(length=2), nullable=False),
        sa.Column("state_name", sa.String(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("area_km2", sa.Float(), nullable=True),
        sa.Column("centroid_lat", sa.Float(), nullable=True),
        sa.Column("centroid_lon", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ars"),
    )
    op.create_index(op.f("ix_region_ars"), "region", ["ars"], unique=False)

    op.create_table(
        "indicator_definition",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("methodology", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(
        op.f("ix_indicator_definition_key"), "indicator_definition", ["key"], unique=False
    )

    op.create_table(
        "user_preference_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("climate_weight", sa.Integer(), nullable=False),
        sa.Column("air_weight", sa.Integer(), nullable=False),
        sa.Column("safety_weight", sa.Integer(), nullable=False),
        sa.Column("demographics_weight", sa.Integer(), nullable=False),
        sa.Column("amenities_weight", sa.Integer(), nullable=False),
        sa.Column("oepnv_weight", sa.Integer(), nullable=False),
        sa.Column("urban_preference", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "region_indicator_value",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("indicator_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("normalized_value", sa.Float(), nullable=False),
        sa.Column("quality_flag", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicator_definition.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["region.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_id", "indicator_id", "period"),
    )
    op.create_index(
        op.f("ix_region_indicator_value_indicator_id"),
        "region_indicator_value",
        ["indicator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_region_indicator_value_period"), "region_indicator_value", ["period"], unique=False
    )
    op.create_index(
        op.f("ix_region_indicator_value_region_id"),
        "region_indicator_value",
        ["region_id"],
        unique=False,
    )

    op.create_table(
        "region_score_snapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("profile_key", sa.String(), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("score_total", sa.Float(), nullable=False),
        sa.Column("score_climate", sa.Float(), nullable=False),
        sa.Column("score_air", sa.Float(), nullable=False),
        sa.Column("score_safety", sa.Float(), nullable=False),
        sa.Column("score_demographics", sa.Float(), nullable=False),
        sa.Column("score_amenities", sa.Float(), nullable=False),
        sa.Column("score_oepnv", sa.Float(), nullable=False),
        sa.Column("explanation_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["region.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_id", "profile_key", "period"),
    )
    op.create_index(
        op.f("ix_region_score_snapshot_period"), "region_score_snapshot", ["period"], unique=False
    )
    op.create_index(
        op.f("ix_region_score_snapshot_profile_key"),
        "region_score_snapshot",
        ["profile_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_region_score_snapshot_region_id"),
        "region_score_snapshot",
        ["region_id"],
        unique=False,
    )

    op.execute("CREATE SCHEMA IF NOT EXISTS osm")

    op.create_table(
        "poi_category_map",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("osm_key", sa.String(), nullable=False),
        sa.Column("osm_value", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("osm_key", "osm_value", name="uq_poi_category_map_key_value"),
        schema="osm",
    )

    op.create_table(
        "region_amenity_agg",
        sa.Column("ars", sa.String(length=12), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("count_total", sa.Integer(), nullable=False),
        sa.Column("per_10k", sa.Numeric(12, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("ars", "category"),
        schema="osm",
    )


def downgrade() -> None:
    op.drop_table("region_amenity_agg", schema="osm")
    op.drop_table("poi_category_map", schema="osm")

    op.drop_index(op.f("ix_region_score_snapshot_region_id"), table_name="region_score_snapshot")
    op.drop_index(op.f("ix_region_score_snapshot_profile_key"), table_name="region_score_snapshot")
    op.drop_index(op.f("ix_region_score_snapshot_period"), table_name="region_score_snapshot")
    op.drop_table("region_score_snapshot")

    op.drop_index(op.f("ix_region_indicator_value_region_id"), table_name="region_indicator_value")
    op.drop_index(op.f("ix_region_indicator_value_period"), table_name="region_indicator_value")
    op.drop_index(
        op.f("ix_region_indicator_value_indicator_id"), table_name="region_indicator_value"
    )
    op.drop_table("region_indicator_value")

    op.drop_table("user_preference_session")
    op.drop_index(op.f("ix_indicator_definition_key"), table_name="indicator_definition")
    op.drop_table("indicator_definition")
    op.drop_index(op.f("ix_region_ars"), table_name="region")
    op.drop_table("region")
    op.execute("DROP SCHEMA IF EXISTS osm CASCADE")
    op.execute("DROP EXTENSION IF EXISTS hstore")
    op.execute("DROP EXTENSION IF EXISTS postgis")

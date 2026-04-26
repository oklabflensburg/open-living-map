"""Add coverage fields to region_score_snapshot

Revision ID: 20260420_0013
Revises: 20260420_0012
Create Date: 2026-04-20 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260420_0013"
down_revision = "20260420_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add coverage columns to region_score_snapshot
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_climate", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_air", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_safety", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_demographics", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_amenities", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_landuse", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "region_score_snapshot",
        sa.Column("coverage_oepnv", sa.Float(), nullable=False, server_default="0.0"),
    )

    # Create indexes for coverage fields to support filtering
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_climate"),
        "region_score_snapshot",
        ["coverage_climate"],
    )
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_air"), "region_score_snapshot", ["coverage_air"]
    )
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_safety"),
        "region_score_snapshot",
        ["coverage_safety"],
    )
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_demographics"),
        "region_score_snapshot",
        ["coverage_demographics"],
    )
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_amenities"),
        "region_score_snapshot",
        ["coverage_amenities"],
    )
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_landuse"),
        "region_score_snapshot",
        ["coverage_landuse"],
    )
    op.create_index(
        op.f("ix_region_score_snapshot_coverage_oepnv"), "region_score_snapshot", ["coverage_oepnv"]
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(
        op.f("ix_region_score_snapshot_coverage_oepnv"), table_name="region_score_snapshot"
    )
    op.drop_index(
        op.f("ix_region_score_snapshot_coverage_landuse"), table_name="region_score_snapshot"
    )
    op.drop_index(
        op.f("ix_region_score_snapshot_coverage_amenities"), table_name="region_score_snapshot"
    )
    op.drop_index(
        op.f("ix_region_score_snapshot_coverage_demographics"), table_name="region_score_snapshot"
    )
    op.drop_index(
        op.f("ix_region_score_snapshot_coverage_safety"), table_name="region_score_snapshot"
    )
    op.drop_index(op.f("ix_region_score_snapshot_coverage_air"), table_name="region_score_snapshot")
    op.drop_index(
        op.f("ix_region_score_snapshot_coverage_climate"), table_name="region_score_snapshot"
    )

    # Drop columns
    op.drop_column("region_score_snapshot", "coverage_oepnv")
    op.drop_column("region_score_snapshot", "coverage_landuse")
    op.drop_column("region_score_snapshot", "coverage_amenities")
    op.drop_column("region_score_snapshot", "coverage_demographics")
    op.drop_column("region_score_snapshot", "coverage_safety")
    op.drop_column("region_score_snapshot", "coverage_air")
    op.drop_column("region_score_snapshot", "coverage_climate")

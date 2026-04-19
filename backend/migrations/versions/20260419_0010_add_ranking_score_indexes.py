"""add ranking score indexes

Revision ID: 20260419_0010
Revises: 20260419_0009
Create Date: 2026-04-19 11:40:00
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260419_0010"
down_revision: str | None = "20260419_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for index_sql in [
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_rank_climate
        ON region_score_snapshot (profile_key, period, score_climate DESC, region_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_rank_air
        ON region_score_snapshot (profile_key, period, score_air DESC, region_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_rank_safety
        ON region_score_snapshot (profile_key, period, score_safety DESC, region_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_rank_demographics
        ON region_score_snapshot (profile_key, period, score_demographics DESC, region_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_rank_amenities
        ON region_score_snapshot (profile_key, period, score_amenities DESC, region_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_rank_oepnv
        ON region_score_snapshot (profile_key, period, score_oepnv DESC, region_id);
        """,
    ]:
        op.execute(index_sql)


def downgrade() -> None:
    for index_sql in [
        "DROP INDEX IF EXISTS ix_region_score_snapshot_rank_climate;",
        "DROP INDEX IF EXISTS ix_region_score_snapshot_rank_air;",
        "DROP INDEX IF EXISTS ix_region_score_snapshot_rank_safety;",
        "DROP INDEX IF EXISTS ix_region_score_snapshot_rank_demographics;",
        "DROP INDEX IF EXISTS ix_region_score_snapshot_rank_amenities;",
        "DROP INDEX IF EXISTS ix_region_score_snapshot_rank_oepnv;",
    ]:
        op.execute(index_sql)

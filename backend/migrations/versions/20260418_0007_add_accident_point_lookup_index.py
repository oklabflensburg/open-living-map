"""add accident point lookup index

Revision ID: 20260418_0007
Revises: 20260417_0006
Create Date: 2026-04-18 10:20:00
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260418_0007"
down_revision: str | None = "20260417_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('traffic.accident_point') IS NOT NULL THEN
                CREATE INDEX IF NOT EXISTS accident_point_region_category_idx
                ON traffic.accident_point (region_ars, category);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS traffic.accident_point_region_category_idx")

"""make region slug unique

Revision ID: 20260420_0018
Revises: 20260420_0017
Create Date: 2026-04-20 23:55:00
"""

from alembic import op


revision = "20260420_0018"
down_revision = "20260420_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ars,
                slug,
                ROW_NUMBER() OVER (PARTITION BY slug ORDER BY ars, id) AS rn
            FROM region
            WHERE slug IS NOT NULL
              AND slug <> ''
        )
        UPDATE region r
        SET slug = ranked.slug || '-' || ranked.ars
        FROM ranked
        WHERE r.id = ranked.id
          AND ranked.rn > 1;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_region_slug
        ON region (slug)
        WHERE slug IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_region_slug;")

"""add region slug index

Revision ID: 20260417_0006
Revises: 20260417_0005
Create Date: 2026-04-17 17:18:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260417_0006"
down_revision: str | None = "20260417_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_region_slug ON region (slug)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_region_slug")

"""add indicator normalization mode

Revision ID: 20260419_0008
Revises: 20260418_0007
Create Date: 2026-04-19 10:35:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260419_0008"
down_revision: str | None = "20260418_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE indicator_definition
        ADD COLUMN IF NOT EXISTS normalization_mode text DEFAULT 'log' NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE indicator_definition
        DROP COLUMN IF EXISTS normalization_mode;
        """
    )

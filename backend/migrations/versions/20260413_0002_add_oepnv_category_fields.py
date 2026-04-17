"""add oepnv category fields

Revision ID: 20260413_0002
Revises: 20260413_0001
Create Date: 2026-04-13 13:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260413_0002"
down_revision: str | None = "20260413_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "region_score_snapshot",
        sa.Column("score_oepnv", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "user_preference_session",
        sa.Column("oepnv_weight", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("user_preference_session", "oepnv_weight")
    op.drop_column("region_score_snapshot", "score_oepnv")

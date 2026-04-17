"""add oepnv category fields

Revision ID: 20260413_0002
Revises: 20260413_0001
Create Date: 2026-04-13 13:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "20260413_0002"
down_revision: str | None = "20260413_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    snapshot_columns = {column["name"] for column in inspector.get_columns("region_score_snapshot")}
    preference_columns = {column["name"] for column in inspector.get_columns("user_preference_session")}

    if "score_oepnv" not in snapshot_columns:
        op.add_column(
            "region_score_snapshot",
            sa.Column("score_oepnv", sa.Float(), nullable=False, server_default=sa.text("0")),
        )

    if "oepnv_weight" not in preference_columns:
        op.add_column(
            "user_preference_session",
            sa.Column("oepnv_weight", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    op.drop_column("user_preference_session", "oepnv_weight")
    op.drop_column("region_score_snapshot", "score_oepnv")

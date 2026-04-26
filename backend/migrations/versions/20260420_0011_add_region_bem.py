"""add region bem column

Revision ID: 20260420_0011
Revises: 20260419_0010
Create Date: 2026-04-20 09:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260420_0011"
down_revision: str | None = "20260419_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("region")}
    if "bem" not in columns:
        op.add_column("region", sa.Column("bem", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("region")}
    if "bem" in columns:
        op.drop_column("region", "bem")

"""add region wiki links

Revision ID: 20260414_0003
Revises: 20260413_0002
Create Date: 2026-04-14 13:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260414_0003"
down_revision: str | None = "20260413_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("region", sa.Column("wikidata_id", sa.String(), nullable=True))
    op.add_column("region", sa.Column("wikidata_url", sa.String(), nullable=True))
    op.add_column("region", sa.Column("wikipedia_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("region", "wikipedia_url")
    op.drop_column("region", "wikidata_url")
    op.drop_column("region", "wikidata_id")

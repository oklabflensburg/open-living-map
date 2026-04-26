"""add persisted region slug

Revision ID: 20260417_0005
Revises: 20260417_0004
Create Date: 2026-04-17 17:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.core.ars import slugify_region_name

# revision identifiers, used by Alembic.
revision: str = "20260417_0005"
down_revision: str | None = "20260417_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("region")}
    indexes = {index["name"] for index in inspector.get_indexes("region")}

    if "slug" not in columns:
        op.add_column("region", sa.Column("slug", sa.String(), nullable=True))

    if "ix_region_slug" not in indexes:
        op.create_index("ix_region_slug", "region", ["slug"], unique=False)

    region = sa.table(
        "region",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
    )
    rows = bind.execute(
        sa.select(region.c.id, region.c.name).where(
            sa.or_(region.c.slug.is_(None), region.c.slug == "")
        )
    ).all()
    for row_id, name in rows:
        bind.execute(
            sa.update(region)
            .where(region.c.id == row_id)
            .values(slug=slugify_region_name(str(name)))
        )


def downgrade() -> None:
    op.drop_index("ix_region_slug", table_name="region")
    op.drop_column("region", "slug")

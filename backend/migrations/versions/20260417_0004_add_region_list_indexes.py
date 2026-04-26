"""add indexes for region list and common lookups

Revision ID: 20260417_0004
Revises: 20260414_0003
Create Date: 2026-04-17 16:55:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260417_0004"
down_revision = "20260414_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_region_name", "region", ["name"], unique=False)
    op.create_index("ix_region_state_code_name", "region", ["state_code", "name"], unique=False)
    op.create_index(
        "ix_indicator_definition_source_url",
        "indicator_definition",
        ["source_url"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_indicator_definition_source_url", table_name="indicator_definition")
    op.drop_index("ix_region_state_code_name", table_name="region")
    op.drop_index("ix_region_name", table_name="region")

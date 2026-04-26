"""add region postal code table

Revision ID: 20260420_0017
Revises: 20260420_0016
Create Date: 2026-04-20 23:20:00
"""

from alembic import op

revision = "20260420_0017"
down_revision = "20260420_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS postal;")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS postal.region_postal_code (
            postal_code varchar(5) NOT NULL,
            region_ars varchar(12) NOT NULL,
            region_name varchar NOT NULL,
            postal_name varchar NULL,
            overlap_area double precision NULL,
            is_primary boolean NOT NULL DEFAULT false,
            updated_at timestamp without time zone NOT NULL,
            PRIMARY KEY (postal_code, region_ars)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_region_postal_code_code
        ON postal.region_postal_code (postal_code);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_region_postal_code_region_ars
        ON postal.region_postal_code (region_ars);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_region_postal_code_primary
        ON postal.region_postal_code (postal_code, is_primary);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS postal.region_postal_code;")
    op.execute("DROP SCHEMA IF EXISTS postal;")

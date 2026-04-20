"""Add index for user_preference_session retention cleanup

Revision ID: 20260420_0014
Revises: 20260420_0013
Create Date: 2026-04-20 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260420_0014'
down_revision = '20260420_0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure created_at column exists and has an index for retention cleanup
    op.create_index('ix_user_preference_session_created_at', 'user_preference_session', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_user_preference_session_created_at', table_name='user_preference_session')

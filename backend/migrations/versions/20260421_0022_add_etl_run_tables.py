"""add etl run tables

Revision ID: 20260421_0022
Revises: 20260421_0021
Create Date: 2026-04-21 02:00:00
"""

from alembic import op


revision = "20260421_0022"
down_revision = "20260421_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS etl_run (
            id serial PRIMARY KEY,
            job_name varchar NOT NULL,
            status varchar NOT NULL DEFAULT 'running',
            rows_written integer NULL,
            error_message text NULL,
            started_at timestamp without time zone NOT NULL DEFAULT now(),
            finished_at timestamp without time zone NULL
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_etl_run_job_name
        ON etl_run (job_name);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_etl_run_status
        ON etl_run (status);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_etl_run_started_at
        ON etl_run (started_at);
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS etl_run_source (
            id serial PRIMARY KEY,
            etl_run_id integer NOT NULL REFERENCES etl_run(id) ON DELETE CASCADE,
            source_name varchar NOT NULL,
            source_url varchar NULL,
            source_version varchar NULL,
            source_hash varchar NULL
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_etl_run_source_etl_run_id
        ON etl_run_source (etl_run_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS etl_run_source;")
    op.execute("DROP TABLE IF EXISTS etl_run;")

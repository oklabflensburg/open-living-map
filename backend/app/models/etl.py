from datetime import datetime

from sqlmodel import Field, SQLModel


class EtlRun(SQLModel, table=True):
    __tablename__ = "etl_run"

    id: int | None = Field(default=None, primary_key=True)
    job_name: str = Field(index=True)
    status: str = Field(index=True, default="running")
    rows_written: int | None = None
    error_message: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    finished_at: datetime | None = None


class EtlRunSource(SQLModel, table=True):
    __tablename__ = "etl_run_source"

    id: int | None = Field(default=None, primary_key=True)
    etl_run_id: int = Field(foreign_key="etl_run.id", index=True)
    source_name: str
    source_url: str | None = None
    source_version: str | None = None
    source_hash: str | None = None

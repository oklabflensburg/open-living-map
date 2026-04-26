from datetime import datetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class RegionScoreSnapshot(SQLModel, table=True):
    __tablename__ = "region_score_snapshot"
    __table_args__ = (UniqueConstraint("region_id", "profile_key", "period"),)

    id: int | None = Field(default=None, primary_key=True)
    region_id: int = Field(foreign_key="region.id", index=True)
    profile_key: str = Field(index=True, default="base")
    period: str = Field(index=True)
    score_total: float = 0
    score_climate: float = 0
    score_air: float = 0
    score_safety: float = 0
    score_demographics: float = 0
    score_amenities: float = 0
    score_landuse: float = 0
    score_oepnv: float = 0

    """
    Coverage fields: percentage of indicators available per
    category (0.0 to 1.0)
    """
    coverage_climate: float = Field(default=0.0)
    coverage_air: float = Field(default=0.0)
    coverage_safety: float = Field(default=0.0)
    coverage_demographics: float = Field(default=0.0)
    coverage_amenities: float = Field(default=0.0)
    coverage_landuse: float = Field(default=0.0)
    coverage_oepnv: float = Field(default=0.0)
    explanation_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow)

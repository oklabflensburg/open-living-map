from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class IndicatorDefinition(SQLModel, table=True):
    __tablename__ = "indicator_definition"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    name: str
    category: str
    unit: str
    direction: str
    source_name: str
    source_url: str
    methodology: str


class RegionIndicatorValue(SQLModel, table=True):
    __tablename__ = "region_indicator_value"
    __table_args__ = (UniqueConstraint("region_id", "indicator_id", "period"),)

    id: int | None = Field(default=None, primary_key=True)
    region_id: int = Field(foreign_key="region.id", index=True)
    indicator_id: int = Field(foreign_key="indicator_definition.id", index=True)
    period: str = Field(index=True)
    raw_value: float
    normalized_value: float
    quality_flag: str = Field(default="ok")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

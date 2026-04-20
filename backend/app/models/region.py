from typing import Optional

from sqlmodel import Field, SQLModel


class Region(SQLModel, table=True):
    __tablename__ = "region"

    id: int | None = Field(default=None, primary_key=True)
    ars: str = Field(index=True, unique=True, max_length=12)
    bem: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, index=True)
    name: str
    level: str = Field(default="kreis")
    state_code: str = Field(max_length=2)
    state_name: str
    district_name: str | None = None
    population: int | None = None
    area_km2: float | None = None
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    wikidata_id: str | None = None
    wikidata_url: str | None = None
    wikipedia_url: str | None = None

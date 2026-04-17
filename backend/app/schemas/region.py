from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.ars import slugify_region_name
from app.schemas.recommendation import RecommendationIndicatorDetail


class RegionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ars: str
    name: str
    level: str
    state_code: str
    state_name: str
    population: int | None
    area_km2: float | None
    centroid_lat: float | None
    centroid_lon: float | None
    wikidata_id: str | None
    wikidata_url: str | None
    wikipedia_url: str | None

    @computed_field
    @property
    def slug(self) -> str:
        return slugify_region_name(self.name)


class RegionListResponse(BaseModel):
    items: list[RegionBase]


class AmenityStat(BaseModel):
    category: str
    label: str
    count_total: int
    per_10k: float


class AccidentStat(BaseModel):
    category: str
    label: str
    count_total: int


class RegionDetailResponse(BaseModel):
    region: RegionBase
    scores: dict[str, float]
    highlights: list[str]
    source_links: list[str]
    amenity_stats: list[AmenityStat] = []
    accident_stats: list[AccidentStat] = []
    geometry: dict[str, Any] | None = None
    score_formula: str = ""
    calculation_details: list[str] = []
    indicators: list[RecommendationIndicatorDetail] = []

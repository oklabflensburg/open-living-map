from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.recommendation import RecommendationIndicatorDetail


class RegionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ars: str
    slug: str = ""
    name: str
    level: str
    state_code: str
    state_name: str
    district_name: str | None
    population: int | None
    area_km2: float | None
    centroid_lat: float | None
    centroid_lon: float | None
    wikidata_id: str | None
    wikidata_url: str | None
    wikipedia_url: str | None


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


class AirStationInfo(BaseModel):
    indicator_key: str
    label: str
    raw_value: float | None = None
    station_id: str
    station_code: str | None = None
    station_name: str
    latitude: float | None = None
    longitude: float | None = None
    station_page_url: str | None = None
    measures_url: str


class ClimateStationInfo(BaseModel):
    indicator_key: str
    label: str
    raw_value: float | None = None
    station_id: str
    station_name: str
    latitude: float | None = None
    longitude: float | None = None
    source_url: str | None = None


class LandUseStat(BaseModel):
    year: int
    forest_share_pct: float | None = None
    settlement_transport_share_pct: float | None = None
    agriculture_share_pct: float | None = None
    transport_share_pct: float | None = None
    settlement_transport_sqm_per_capita: float | None = None


class ScoreCoverage(BaseModel):
    climate: float = 0.0
    air: float = 0.0
    safety: float = 0.0
    demographics: float = 0.0
    amenities: float = 0.0
    landuse: float = 0.0
    oepnv: float = 0.0


class CategoryFreshness(BaseModel):
    updated_at: datetime | None = None
    sources: list[str] = Field(default_factory=list)


class ScoreFreshness(BaseModel):
    climate: CategoryFreshness = Field(default_factory=CategoryFreshness)
    air: CategoryFreshness = Field(default_factory=CategoryFreshness)
    safety: CategoryFreshness = Field(default_factory=CategoryFreshness)
    demographics: CategoryFreshness = Field(default_factory=CategoryFreshness)
    amenities: CategoryFreshness = Field(default_factory=CategoryFreshness)
    landuse: CategoryFreshness = Field(default_factory=CategoryFreshness)
    oepnv: CategoryFreshness = Field(default_factory=CategoryFreshness)


class CategoryQualitySummary(BaseModel):
    status: str = "ok"
    notes: list[str] = Field(default_factory=list)


class ScoreQualitySummary(BaseModel):
    climate: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)
    air: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)
    safety: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)
    demographics: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)
    amenities: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)
    landuse: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)
    oepnv: CategoryQualitySummary = Field(default_factory=CategoryQualitySummary)


class RegionDetailResponse(BaseModel):
    region: RegionBase
    scores: dict[str, float]
    coverage: ScoreCoverage
    freshness: ScoreFreshness
    quality: ScoreQualitySummary
    highlights: list[str]
    source_links: list[str]
    amenity_stats: list[AmenityStat] = []
    accident_stats: list[AccidentStat] = []
    air_stations: list[AirStationInfo] = []
    climate_stations: list[ClimateStationInfo] = []
    land_use_stat: LandUseStat | None = None
    geometry: dict[str, Any] | None = None
    score_formula: str = ""
    calculation_details: list[str] = []
    indicators: list[RecommendationIndicatorDetail] = []

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
    district_name: str | None
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


class LandUseStat(BaseModel):
    year: int
    forest_share_pct: float | None = None
    settlement_transport_share_pct: float | None = None
    agriculture_share_pct: float | None = None
    transport_share_pct: float | None = None
    settlement_transport_sqm_per_capita: float | None = None


class RegionDetailResponse(BaseModel):
    region: RegionBase
    scores: dict[str, float]
    highlights: list[str]
    source_links: list[str]
    amenity_stats: list[AmenityStat] = []
    accident_stats: list[AccidentStat] = []
    air_stations: list[AirStationInfo] = []
    land_use_stat: LandUseStat | None = None
    geometry: dict[str, Any] | None = None
    score_formula: str = ""
    calculation_details: list[str] = []
    indicators: list[RecommendationIndicatorDetail] = []

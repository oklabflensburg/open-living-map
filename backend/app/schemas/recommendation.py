from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RecommendationInput(BaseModel):
    preset: Literal["family", "transit", "air-climate", "urban", "quiet-nature"] | None = None
    climate_weight: int = Field(ge=0, le=5)
    air_weight: int = Field(ge=0, le=5)
    safety_weight: int = Field(ge=0, le=5)
    demographics_weight: int = Field(ge=0, le=5)
    amenities_weight: int = Field(ge=0, le=5)
    landuse_weight: int = Field(ge=0, le=5)
    oepnv_weight: int = Field(ge=0, le=5)
    state_code: str | None = Field(default=None, pattern=r"^\d{2}$")
    min_climate_score: float | None = Field(default=None, ge=0, le=100)
    min_air_score: float | None = Field(default=None, ge=0, le=100)
    min_safety_score: float | None = Field(default=None, ge=0, le=100)
    min_demographics_score: float | None = Field(default=None, ge=0, le=100)
    min_amenities_score: float | None = Field(default=None, ge=0, le=100)
    min_landuse_score: float | None = Field(default=None, ge=0, le=100)
    min_oepnv_score: float | None = Field(default=None, ge=0, le=100)
    coverage_min: float | None = Field(default=None, ge=0, le=100)

    @field_validator("state_code", mode="before")
    @classmethod
    def normalize_nationwide_state_code(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.lower() in {"", "de", "deutschland", "deutschlandweit", "all"}:
                return None
            return normalized
        return value


class RecommendationIndicatorDetail(BaseModel):
    key: str
    name: str
    category: str
    unit: str
    raw_value: float
    normalized_value: float
    quality_flag: str
    source_name: str
    updated_at: str | None = None
    text: str


class RecommendationItem(BaseModel):
    ars: str
    slug: str
    name: str
    level: str
    state_name: str
    district_name: str | None = None
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    score_total: float
    score_profile: float
    score_climate: float
    score_air: float
    score_safety: float
    score_demographics: float
    score_amenities: float
    score_landuse: float
    score_oepnv: float
    # Coverage fields (0.0 to 1.0)
    coverage_climate: float = 0.0
    coverage_air: float = 0.0
    coverage_safety: float = 0.0
    coverage_demographics: float = 0.0
    coverage_amenities: float = 0.0
    coverage_landuse: float = 0.0
    coverage_oepnv: float = 0.0
    trust_updated_at: str | None = None
    trust_sources: list[str] = Field(default_factory=list)
    trust_quality_notes: list[str] = Field(default_factory=list)
    reason: str
    score_formula: str = ""
    calculation_details: list[str] = Field(default_factory=list)
    indicators: list[RecommendationIndicatorDetail] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]

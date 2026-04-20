from pydantic import BaseModel, Field


class RecommendationInput(BaseModel):
    climate_weight: int = Field(ge=0, le=5)
    air_weight: int = Field(ge=0, le=5)
    safety_weight: int = Field(ge=0, le=5)
    demographics_weight: int = Field(ge=0, le=5)
    amenities_weight: int = Field(ge=0, le=5)
    landuse_weight: int = Field(ge=0, le=5)
    oepnv_weight: int = Field(ge=0, le=5)
    state_code: str | None = Field(default=None, pattern=r"^\d{2}$")


class RecommendationIndicatorDetail(BaseModel):
    key: str
    name: str
    category: str
    unit: str
    raw_value: float
    normalized_value: float
    quality_flag: str
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
    reason: str
    score_formula: str = ""
    calculation_details: list[str] = Field(default_factory=list)
    indicators: list[RecommendationIndicatorDetail] = Field(
        default_factory=list
    )


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]

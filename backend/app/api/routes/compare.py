from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.recommendation import RecommendationInput, RecommendationResponse
from app.services.scoring import ScoringService

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=RecommendationResponse)
def compare(
    ars: str = Query(..., description="Kommagetrennte AGS-Codes (Route ist ARS-kompatibel)"),
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    ars_list = [item.strip() for item in ars.split(",") if item.strip()][:3]
    default_weights = RecommendationInput(
        climate_weight=1,
        air_weight=1,
        safety_weight=1,
        demographics_weight=1,
        amenities_weight=1,
        landuse_weight=1,
        oepnv_weight=1,
    )
    service = ScoringService(session)
    return service.get_recommendations(default_weights, include_ars=ars_list)

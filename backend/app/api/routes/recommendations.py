from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.recommendation import RecommendationInput, RecommendationResponse
from app.services.scoring import ScoringService

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(
    payload: RecommendationInput,
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    service = ScoringService(session)
    return service.get_recommendations(payload)

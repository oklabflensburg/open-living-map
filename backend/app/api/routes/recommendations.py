from fastapi import APIRouter, Depends, Path, Query
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.recommendation import (
    RecommendationInput,
    RecommendationResponse,
)
from app.services.scoring import ScoringService

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(
    payload: RecommendationInput,
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    service = ScoringService(session)
    return service.get_recommendations(payload)


@router.get(
    "/rankings/top/{category}",
    response_model=RecommendationResponse,
)
def top_rankings_by_category(
    category: str = Path(
        pattern=r"^(climate|air|safety|demographics|amenities|oepnv)$"
    ),
    state_code: str | None = Query(default=None, pattern=r"^\d{2}$"),
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    service = ScoringService(session)
    return service.get_top_rankings(
        state_code=state_code,
        category=category,
        limit=limit,
    )


@router.get(
    "/rankings/top/{state_code}/{category}",
    response_model=RecommendationResponse,
)
def top_rankings(
    state_code: str = Path(pattern=r"^\d{2}$"),
    category: str = Path(
        pattern=r"^(climate|air|safety|demographics|amenities|oepnv)$"
    ),
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
) -> RecommendationResponse:
    service = ScoringService(session)
    return service.get_top_rankings(
        state_code=state_code,
        category=category,
        limit=limit,
    )

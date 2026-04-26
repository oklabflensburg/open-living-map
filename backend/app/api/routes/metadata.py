from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.repositories.score_repository import ScoreRepository
from app.schemas.metadata import IndicatorMetadata, IndicatorMetadataResponse

router = APIRouter(tags=["metadata"])


@router.get("/metadata/indicators", response_model=IndicatorMetadataResponse)
def indicator_metadata(session: Session = Depends(get_session)) -> IndicatorMetadataResponse:
    repository = ScoreRepository(session)
    indicators = repository.list_indicators()
    return IndicatorMetadataResponse(
        items=[IndicatorMetadata.model_validate(indicator) for indicator in indicators]
    )

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.db import get_session
from app.repositories.region_repository import RegionRepository
from app.schemas.region import RegionBase, RegionDetailResponse, RegionListResponse
from app.services.regions import RegionService

router = APIRouter(tags=["regions"])


@router.get("/regions", response_model=RegionListResponse)
def list_regions(session: Session = Depends(get_session)) -> RegionListResponse:
    repository = RegionRepository(session)
    regions = repository.list_regions()
    return RegionListResponse(items=[RegionBase.model_validate(region) for region in regions])


@router.get("/regions/{ars}", response_model=RegionDetailResponse)
def get_region(ars: str, session: Session = Depends(get_session)) -> RegionDetailResponse:
    service = RegionService(session)
    detail = service.get_region_detail(ars)
    if detail is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return detail


@router.get("/regions/{ars}/amenities/{category}")
def get_region_amenity_pois(ars: str, category: str, session: Session = Depends(get_session)) -> dict:
    service = RegionService(session)
    geojson = service.get_region_amenity_pois(ars, category)
    if geojson is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return geojson


@router.get("/regions/{ars}/accidents/{category}")
def get_region_accident_pois(ars: str, category: str, session: Session = Depends(get_session)) -> dict:
    service = RegionService(session)
    geojson = service.get_region_accident_pois(ars, category)
    if geojson is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return geojson

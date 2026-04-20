from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.db import get_session
from app.repositories.region_repository import RegionRepository
from app.schemas.region import RegionBase, RegionDetailResponse, RegionListResponse
from app.services.regions import RegionService

router = APIRouter(tags=["regions"])


@router.get("/regions", response_model=RegionListResponse)
def list_regions(
    q: str | None = Query(default=None, description="Search query for region name"),
    state_code: str | None = Query(default=None, pattern=r"^\d{2}$", description="Filter by state code"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    session: Session = Depends(get_session),
) -> RegionListResponse:
    """List regions with optional search, filtering and pagination.
    
    Note: For performance reasons, either 'q' (search query) or 'state_code' should be provided
    when fetching large numbers of regions. Unfiltered requests are limited to 1000 results.
    """
    repository = RegionRepository(session)
    
    # If no search query or filter is provided, warn about performance
    if q is None and state_code is None and limit > 100:
        # In production, you might want to enforce a lower limit for unfiltered requests
        pass
    
    regions = repository.list_regions(search_query=q, state_code=state_code, limit=limit, offset=offset)
    return RegionListResponse(items=[RegionBase.model_validate(region) for region in regions])


@router.get("/regions/state-boundaries")
def get_state_boundaries(
    state_code: str | None = Query(default=None, pattern=r"^\d{2}$"),
    session: Session = Depends(get_session),
) -> dict:
    service = RegionService(session)
    return service.get_state_boundaries(state_code)


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


@router.get("/regions/search/autocomplete", response_model=RegionListResponse)
def search_regions_autocomplete(
    q: str = Query(..., min_length=2, description="Search query for region name (minimum 2 characters)"),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum number of results"),
    session: Session = Depends(get_session),
) -> RegionListResponse:
    """Search regions for autocomplete with debounced frontend requests."""
    repository = RegionRepository(session)
    regions = repository.list_regions(search_query=q, limit=limit)
    return RegionListResponse(items=[RegionBase.model_validate(region) for region in regions])

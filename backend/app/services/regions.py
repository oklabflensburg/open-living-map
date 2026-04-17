from sqlmodel import Session

from app.repositories.region_repository import ACCIDENT_CATEGORY_LABELS, RegionRepository
from app.schemas.recommendation import RecommendationInput
from app.schemas.region import AccidentStat, AmenityStat, RegionBase, RegionDetailResponse
from app.services.scoring import ScoringService


class RegionService:
    def __init__(self, session: Session) -> None:
        self.repository = RegionRepository(session)

    def get_region_detail(self, ars: str) -> RegionDetailResponse | None:
        region = self.repository.get_by_ars(ars)
        if region is None:
            return None

        snapshot = self.repository.get_score_snapshot(region.id)
        scores = {
            "total": snapshot.score_total if snapshot else 0.0,
            "climate": snapshot.score_climate if snapshot else 0.0,
            "air": snapshot.score_air if snapshot else 0.0,
            "safety": snapshot.score_safety if snapshot else 0.0,
            "demographics": snapshot.score_demographics if snapshot else 0.0,
            "amenities": snapshot.score_amenities if snapshot else 0.0,
            "oepnv": snapshot.score_oepnv if snapshot else 0.0,
        }

        highlights = [
            f"Klimascore: {scores['climate']:.1f}",
            f"Luftqualitaet: {scores['air']:.1f}",
            f"Alltagsnaehe: {scores['amenities']:.1f}",
            f"OEPNV: {scores['oepnv']:.1f}",
        ]
        source_links = self.repository.list_source_links()
        amenity_stats = [
            AmenityStat(
                category=category,
                label=ScoringService.amenity_label(category),
                count_total=count_total,
                per_10k=per_10k,
            )
            for category, count_total, per_10k in self.repository.list_amenity_aggregates(region.ars)
        ]
        accident_stats = [
            AccidentStat(
                category=category,
                label=ACCIDENT_CATEGORY_LABELS.get(category, category),
                count_total=count_total,
            )
            for category, count_total in self.repository.list_accident_stats(region.ars)
        ]
        geometry = self.repository.get_boundary_geojson(region.ars)
        base_preferences = RecommendationInput(
            climate_weight=1,
            air_weight=1,
            safety_weight=1,
            demographics_weight=1,
            amenities_weight=1,
            oepnv_weight=1,
        )
        score_formula, calculation_details, indicators = ScoringService(self.repository.session).build_region_explanation(
            ars=region.ars,
            region_id=region.id,
            region_level=region.level,
            region_population=region.population,
            category_scores={
                "climate": scores["climate"],
                "air": scores["air"],
                "safety": scores["safety"],
                "demographics": scores["demographics"],
                "amenities": scores["amenities"],
                "oepnv": scores["oepnv"],
            },
            preferences=base_preferences,
        )

        return RegionDetailResponse(
            region=RegionBase.model_validate(region),
            scores=scores,
            highlights=highlights,
            source_links=source_links,
            amenity_stats=amenity_stats,
            accident_stats=accident_stats,
            geometry=geometry,
            score_formula=score_formula,
            calculation_details=calculation_details,
            indicators=indicators,
        )

    def get_region_amenity_pois(self, ars: str, category: str) -> dict | None:
        region = self.repository.get_by_ars(ars)
        if region is None:
            return None
        return self.repository.get_amenity_pois_geojson(region.ars, category)

    def get_region_accident_pois(self, ars: str, category: str) -> dict | None:
        region = self.repository.get_by_ars(ars)
        if region is None:
            return None
        return self.repository.get_accident_pois_geojson(region.ars, category)

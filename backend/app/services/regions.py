from sqlmodel import Session

from app.repositories.region_repository import ACCIDENT_CATEGORY_LABELS, RegionRepository
from app.schemas.recommendation import RecommendationInput
from app.schemas.region import AccidentStat, AirStationInfo, AmenityStat, RegionBase, RegionDetailResponse
from app.services.scoring import ScoringService

AIR_INDICATOR_LABELS = {
    "no2": "NO2",
    "pm10": "PM10",
    "pm25": "PM2.5",
}


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
            f"Luftqualität: {scores['air']:.1f}",
            f"Alltagsnähe: {scores['amenities']:.1f}",
            f"ÖPNV: {scores['oepnv']:.1f}",
        ]
        source_links = self.repository.list_source_links()
        base_scoring = ScoringService(self.repository.session)
        amenity_stats = [
            AmenityStat(
                category=category,
                label=base_scoring.amenity_label(category),
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
        indicator_values = {indicator.key: indicator for indicator in base_scoring._build_indicator_details(region.id)}
        air_stations = [
            AirStationInfo(
                indicator_key=indicator_key,
                label=AIR_INDICATOR_LABELS.get(indicator_key, indicator_key),
                raw_value=indicator_values.get(indicator_key).raw_value if indicator_values.get(indicator_key) else None,
                station_id=station_id,
                station_code=station_code,
                station_name=station_name,
                latitude=latitude,
                longitude=longitude,
                station_page_url=station_page_url,
                measures_url=measures_url,
            )
            for indicator_key, station_id, station_code, station_name, latitude, longitude, station_page_url, measures_url
            in self.repository.list_air_stations(region.ars)
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
        score_formula, calculation_details, indicators = base_scoring.build_region_explanation(
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
            air_stations=air_stations,
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

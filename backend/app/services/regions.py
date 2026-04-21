from sqlmodel import Session

from app.repositories.region_repository import ACCIDENT_CATEGORY_LABELS, RegionRepository
from app.schemas.recommendation import RecommendationInput
from app.schemas.region import (
    AccidentStat,
    AirStationInfo,
    AmenityStat,
    CategoryFreshness,
    ClimateStationInfo,
    CategoryQualitySummary,
    LandUseStat,
    RegionBase,
    RegionDetailResponse,
    ScoreCoverage,
    ScoreFreshness,
    ScoreQualitySummary,
)
from app.services.scoring import ScoringService

AIR_INDICATOR_LABELS = {
    "no2": "NO2",
    "pm10": "PM10",
    "pm25": "PM2.5",
}

CLIMATE_INDICATOR_LABELS = {
    "heat_days": "Hitzetage",
    "summer_days": "Sommertage",
    "precipitation_proxy": "Niederschlag",
}


class RegionService:
    def __init__(self, session: Session) -> None:
        self.repository = RegionRepository(session)

    def get_region_detail(self, ars: str) -> RegionDetailResponse | None:
        region = self.repository.get_by_ars(ars)
        if region is None:
            return None

        snapshot = self.repository.get_score_snapshot(region.id)
        base_scoring = ScoringService(self.repository.session)
        category_scores = {
            "climate": snapshot.score_climate if snapshot else 0.0,
            "air": snapshot.score_air if snapshot else 0.0,
            "safety": snapshot.score_safety if snapshot else 0.0,
            "demographics": snapshot.score_demographics if snapshot else 0.0,
            "amenities": snapshot.score_amenities if snapshot else 0.0,
            "landuse": snapshot.score_landuse if snapshot else 0.0,
            "oepnv": snapshot.score_oepnv if snapshot else 0.0,
        }
        coverage = {
            "climate": snapshot.coverage_climate if snapshot else 0.0,
            "air": snapshot.coverage_air if snapshot else 0.0,
            "safety": snapshot.coverage_safety if snapshot else 0.0,
            "demographics": snapshot.coverage_demographics if snapshot else 0.0,
            "amenities": snapshot.coverage_amenities if snapshot else 0.0,
            "landuse": snapshot.coverage_landuse if snapshot else 0.0,
            "oepnv": snapshot.coverage_oepnv if snapshot else 0.0,
        }
        freshness_by_category = self.repository.get_category_freshness(region.id)
        freshness = {
            category: CategoryFreshness(**freshness_by_category.get(category, {}))
            for category in category_scores
        }
        base_preferences = RecommendationInput(
            climate_weight=1,
            air_weight=1,
            safety_weight=1,
            demographics_weight=1,
            amenities_weight=1,
            landuse_weight=1,
            oepnv_weight=1,
        )
        scores = {
            "total": snapshot.score_total if snapshot else 0.0,
            **category_scores,
        }

        highlights = [
            f"Klimascore: {scores['climate']:.1f}",
            f"Luftqualität: {scores['air']:.1f}",
            f"Alltagsnähe: {scores['amenities']:.1f}",
            f"Flächennutzung: {scores['landuse']:.1f}",
            f"ÖPNV: {scores['oepnv']:.1f}",
        ]
        source_links = self.repository.list_source_links()
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
        indicator_rows = base_scoring.repository.list_indicator_values(region.id)
        indicator_details = base_scoring._build_indicator_details(indicator_rows)
        quality_by_category = base_scoring.build_category_quality_summary(indicator_rows)
        quality = {
            category: CategoryQualitySummary(**quality_by_category.get(category, {}))
            for category in category_scores
        }
        indicator_values = {indicator.key: indicator for indicator in indicator_details}
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
        climate_stations = [
            ClimateStationInfo(
                indicator_key=indicator_key,
                label=CLIMATE_INDICATOR_LABELS.get(indicator_key, indicator_key),
                raw_value=indicator_values.get(indicator_key).raw_value if indicator_values.get(indicator_key) else None,
                station_id=station_id,
                station_name=station_name,
                latitude=latitude,
                longitude=longitude,
                source_url=source_url,
            )
            for indicator_key, station_id, station_name, latitude, longitude, source_url
            in self.repository.list_climate_stations(region.ars)
        ]
        land_use_stat_row = self.repository.get_land_use_stat(region.ars)
        land_use_stat = (
            LandUseStat(
                year=land_use_stat_row[0],
                forest_share_pct=land_use_stat_row[1],
                settlement_transport_share_pct=land_use_stat_row[2],
                agriculture_share_pct=land_use_stat_row[3],
                transport_share_pct=land_use_stat_row[4],
                settlement_transport_sqm_per_capita=land_use_stat_row[5],
            )
            if land_use_stat_row
            else None
        )
        geometry = self.repository.get_boundary_geojson(region.ars)
        score_formula, calculation_details = base_scoring._build_calculation_details(
            ars=region.ars,
            region_level=region.level,
            region_population=region.population,
            category_scores=category_scores,
            preferences=base_preferences,
            indicators=indicator_details,
            coverage=coverage,
        )

        return RegionDetailResponse(
            region=RegionBase.model_validate(region),
            scores=scores,
            coverage=ScoreCoverage(**coverage),
            freshness=ScoreFreshness(**freshness),
            quality=ScoreQualitySummary(**quality),
            highlights=highlights,
            source_links=source_links,
            amenity_stats=amenity_stats,
            accident_stats=accident_stats,
            air_stations=air_stations,
            climate_stations=climate_stations,
            land_use_stat=land_use_stat,
            geometry=geometry,
            score_formula=score_formula,
            calculation_details=calculation_details,
            indicators=indicator_details,
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

    def get_state_boundaries(self, state_code: str | None) -> dict:
        return self.repository.get_state_boundaries_geojson(state_code)

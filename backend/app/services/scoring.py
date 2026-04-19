from sqlmodel import Session

from app.models.preference import UserPreferenceSession
from app.core.ars import slugify_region_name
from app.repositories.score_repository import ScoreRepository
from app.schemas.recommendation import (
    RecommendationIndicatorDetail,
    RecommendationInput,
    RecommendationItem,
    RecommendationResponse,
)
from app.services.explanations import build_reason

CATEGORY_LABELS = {
    "climate": "Klima",
    "air": "Luftqualität",
    "safety": "Verkehrssicherheit",
    "demographics": "Demografie/Familie",
    "amenities": "Alltagsnähe",
    "landuse": "Flächennutzung",
    "oepnv": "ÖPNV",
}

INDICATOR_LABELS = {
    "heat_days": "Hitzetage",
    "summer_days": "Sommertage",
    "precipitation_proxy": "Niederschlag",
    "no2": "NO2",
    "pm10": "PM10",
    "pm25": "PM2.5",
    "road_accidents_total": "Verkehrsunfälle",
    "population_total_destatis": "Einwohner",
    "female_share_destatis": "Frauenanteil",
    "youth_share_destatis": "Anteil unter 18 Jahren",
    "senior_share_destatis": "Anteil ab 65 Jahren",
    "forest_share_pct": "Waldanteil",
    "settlement_transport_share_pct": "Siedlungs- und Verkehrsflächenanteil",
    "agriculture_share_pct": "Landwirtschaftsanteil",
    "transport_share_pct": "Verkehrsflächenanteil",
    "settlement_transport_sqm_per_capita": "Siedlungs- und Verkehrsfläche je Einwohner",
    "amenities_density": "OSM-POI-Dichte",
    "oepnv_stop_density": "Haltestellendichte",
    "oepnv_departures_per_10k": "Abfahrtsdichte",
    "oepnv_departure_regularity": "Regelmäßigkeit",
}

UNIT_LABELS = {
    "percent": "Prozent",
    "count": "Anzahl",
    "ug/m3": "µg/m³",
    "mm": "mm",
    "per_10k": "je 10.000 Einwohner",
    "departures_per_10k": "Abfahrten je 10.000 Einwohner",
    "stops_per_10k": "Haltestellen je 10.000 Einwohner",
    "sqm_per_capita": "m² je Einwohner",
    "index_0_100": "Index von 0 bis 100",
}

QUALITY_FLAG_LABELS = {
    "ok": "ohne besonderen Hinweis",
    "nearest_station_proxy": "Proxy aus nächstgelegener Messstation",
    "low_coverage": "geringe Abdeckung",
}

AMENITY_LABELS = {
    "pharmacy": "Apotheken",
    "doctors": "Ärzte",
    "hospital": "Krankenhäuser",
    "childcare": "Kitas/Kindergarten",
    "school": "Schulen",
    "supermarket": "Supermärkte",
    "station": "Bahnhöfe",
    "transit_stop": "Haltestellen",
    "playground": "Spielplätze",
    "park": "Parks",
    "museum": "Museen",
    "theatre": "Theater",
    "sports_facility": "Sporteinrichtungen",
    "theme_park": "Tierparks/Freizeitparks",
    "nature_reserve": "Naturschutzgebiete",
    "airfield": "Flugplätze",
    "restaurant": "Restaurants/Gastronomie",
    "library": "Bibliotheken",
}


class ScoringService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ScoreRepository(session)
        self._district_name_cache: dict[str, str | None] = {}

    @staticmethod
    def amenity_label(category: str) -> str:
        return AMENITY_LABELS.get(category, category)

    @staticmethod
    def weighted_total(category_scores: dict[str, float], preferences: RecommendationInput) -> float:
        weights = {
            "climate": preferences.climate_weight,
            "air": preferences.air_weight,
            "safety": preferences.safety_weight,
            "demographics": preferences.demographics_weight,
            "amenities": preferences.amenities_weight,
            "landuse": preferences.landuse_weight,
            "oepnv": preferences.oepnv_weight,
        }
        denominator = sum(weights.values())
        if denominator == 0:
            return 0.0
        numerator = sum(
            category_scores[key] * weight for key, weight in weights.items()
        )
        return round(numerator / denominator, 2)

    @staticmethod
    def preferences_for_category(
        category: str,
        state_code: str | None = None,
    ) -> RecommendationInput:
        weights = {
            'climate_weight': 0,
            'air_weight': 0,
            'safety_weight': 0,
            'demographics_weight': 0,
            'amenities_weight': 0,
            'landuse_weight': 0,
            'oepnv_weight': 0,
        }
        weight_key = f'{category}_weight'
        if weight_key not in weights:
            raise ValueError(f'Unknown category: {category}')
        weights[weight_key] = 5
        return RecommendationInput(**weights, state_code=state_code)

    def _persist_preference_session(self, preferences: RecommendationInput) -> None:
        row = UserPreferenceSession(
            climate_weight=preferences.climate_weight,
            air_weight=preferences.air_weight,
            safety_weight=preferences.safety_weight,
            demographics_weight=preferences.demographics_weight,
            amenities_weight=preferences.amenities_weight,
            landuse_weight=preferences.landuse_weight,
            oepnv_weight=preferences.oepnv_weight,
        )
        self.session.add(row)
        self.session.commit()

    @staticmethod
    def _weights(preferences: RecommendationInput) -> dict[str, int]:
        return {
            "climate": preferences.climate_weight,
            "air": preferences.air_weight,
            "safety": preferences.safety_weight,
            "demographics": preferences.demographics_weight,
            "amenities": preferences.amenities_weight,
            "landuse": preferences.landuse_weight,
            "oepnv": preferences.oepnv_weight,
        }

    @staticmethod
    def _format_value(value: float, unit: str) -> str:
        if unit == "percent":
            return f"{value:.1f} %"
        if unit in {"count", "index_0_100"}:
            return f"{value:,.0f}".replace(",", ".")
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def localized_indicator_name(key: str, fallback: str | None = None) -> str:
        return INDICATOR_LABELS.get(key, fallback or key)

    @staticmethod
    def localized_unit(unit: str) -> str:
        return UNIT_LABELS.get(unit, unit)

    @staticmethod
    def localized_quality_flag(flag: str) -> str:
        return QUALITY_FLAG_LABELS.get(flag, flag)

    def _district_name_for_region(self, ars: str, level: str, district_name: str | None) -> str | None:
        if level != "gemeinde":
            return district_name
        if district_name:
            return district_name
        if ars not in self._district_name_cache:
            self._district_name_cache[ars] = self.repository.resolve_district_name(ars)
        return self._district_name_cache[ars]

    def _indicator_text(self, key: str, raw_value: float, normalized_value: float, unit: str) -> str:
        label = self.localized_indicator_name(key)
        formatted = self._format_value(raw_value, unit)
        localized_unit = self.localized_unit(unit)
        return f"{label}: Rohwert {formatted} ({localized_unit}), normierter Teil-Score {normalized_value:.1f} von 100."

    def _build_indicator_details(self, region_id: int) -> list[RecommendationIndicatorDetail]:
        details: list[RecommendationIndicatorDetail] = []
        for definition, value in self.repository.list_indicator_values(region_id):
            details.append(
                RecommendationIndicatorDetail(
                    key=definition.key,
                    name=self.localized_indicator_name(definition.key, definition.name),
                    category=definition.category,
                    unit=definition.unit,
                    raw_value=value.raw_value,
                    normalized_value=value.normalized_value,
                    quality_flag=self.localized_quality_flag(value.quality_flag),
                    text=self._indicator_text(
                        definition.key,
                        value.raw_value,
                        value.normalized_value,
                        definition.unit,
                    ),
                )
            )
        return details

    def _build_calculation_details(
        self,
        *,
        ars: str,
        region_level: str,
        region_population: int | None,
        category_scores: dict[str, float],
        preferences: RecommendationInput,
        indicators: list[RecommendationIndicatorDetail],
    ) -> tuple[str, list[str]]:
        weights = self._weights(preferences)
        denominator = sum(weights.values())
        if denominator == 0:
            return "Alle Gewichte sind 0, deshalb ist der Gesamtscore 0.", [
                "Keine Kategorie fließt in die Bewertung ein, weil alle Gewichtungen auf 0 stehen."
            ]

        formula_parts = [
            f"{CATEGORY_LABELS[key]} {category_scores[key]:.1f} x {weight}"
            for key, weight in weights.items()
            if weight > 0
        ]
        score_formula = f"Gesamtscore = ({' + '.join(formula_parts)}) / {denominator}"

        details = [
            (
                f"{CATEGORY_LABELS[key]} trägt mit Gewicht {weight}/{denominator} bei: "
                f"{category_scores[key]:.1f} x {weight} / {denominator} = "
                f"{(category_scores[key] * weight / denominator):.1f} Punkte."
            )
            for key, weight in weights.items()
            if weight > 0
        ]

        by_key = {item.key: item for item in indicators}
        population_indicator = by_key.get("population_total_destatis")
        population_value = float(region_population) if region_population is not None else (
            population_indicator.raw_value if population_indicator else None
        )
        female_share = by_key.get("female_share_destatis")
        youth_share = by_key.get("youth_share_destatis")
        senior_share = by_key.get("senior_share_destatis")
        if region_level == "gemeinde" and not any([population_indicator, female_share, youth_share, senior_share]):
            details.append(
                "Demografie-Indikatoren für diese Gemeinde sind aktuell nicht geladen. "
                "Sobald der Regionalstatistik-Import auf Gemeindeebene erfolgreich läuft, erscheinen hier echte Werte."
            )
        if population_value is not None:
            if region_level == "gemeinde" and region_population is not None:
                details.append(f"Einwohner laut Gemeindedatensatz: {self._format_value(population_value, 'count')}.")
            elif region_population is not None:
                details.append(f"Einwohner laut Regionsdatensatz: {self._format_value(population_value, 'count')}.")
            else:
                details.append(f"Einwohner laut Destatis-Indikator: {self._format_value(population_value, 'count')}.")
        if female_share:
            label = "Frauenanteil laut Destatis-Indikator"
            details.append(f"{label}: {self._format_value(female_share.raw_value, female_share.unit)}.")
        if youth_share:
            label = "Anteil unter 18 Jahren laut Destatis-Indikator"
            details.append(f"{label}: {self._format_value(youth_share.raw_value, youth_share.unit)}.")
        if senior_share:
            label = "Anteil ab 65 Jahren laut Destatis-Indikator"
            details.append(f"{label}: {self._format_value(senior_share.raw_value, senior_share.unit)}.")

        amenities = by_key.get("amenities_density")
        if amenities:
            amenity_rows = self.repository.list_amenity_aggregates(ars)
            if amenity_rows:
                amenity_parts = [
                    f"{ScoringService.amenity_label(category)}: {count_total} gesamt, {per_10k:.2f} je 10.000 Einwohner"
                    for category, count_total, per_10k in amenity_rows
                ]
                details.append("OSM-Alltagsnähe nach Kategorien: " + "; ".join(amenity_parts) + ".")
            else:
                details.append(
                    "Alltagsnähe basiert aktuell auf der aggregierten OSM-POI-Dichte. "
                    "Separate Apotheken- oder Ärztezahlen werden angezeigt, sobald `import_osm` erneut gelaufen ist."
                )

        return score_formula, details

    def build_region_explanation(
        self,
        *,
        ars: str,
        region_id: int,
        region_level: str,
        region_population: int | None,
        category_scores: dict[str, float],
        preferences: RecommendationInput,
    ) -> tuple[str, list[str], list[RecommendationIndicatorDetail]]:
        indicators = self._build_indicator_details(region_id)
        score_formula, calculation_details = self._build_calculation_details(
            ars=ars,
            region_level=region_level,
            region_population=region_population,
            category_scores=category_scores,
            preferences=preferences,
            indicators=indicators,
        )
        return score_formula, calculation_details, indicators

    def get_recommendations(
        self,
        preferences: RecommendationInput,
        include_ars: list[str] | None = None,
        limit: int = 10,
        include_details: bool = True,
        persist_session: bool = True,
    ) -> RecommendationResponse:
        if persist_session:
            self._persist_preference_session(preferences)
        rows = self.repository.list_snapshots(
            include_ars=include_ars,
            state_code=preferences.state_code,
        )

        items: list[RecommendationItem] = []
        for region, snapshot in rows:
            category_scores = {
                "climate": snapshot.score_climate,
                "air": snapshot.score_air,
                "safety": snapshot.score_safety,
                "demographics": snapshot.score_demographics,
                "amenities": snapshot.score_amenities,
                "landuse": snapshot.score_landuse,
                "oepnv": snapshot.score_oepnv,
            }
            total = self.weighted_total(category_scores, preferences)
            items.append(
                RecommendationItem(
                    ars=region.ars,
                    slug=slugify_region_name(region.name),
                    name=region.name,
                    level=region.level,
                    state_name=region.state_name,
                    district_name=self._district_name_for_region(region.ars, region.level, region.district_name),
                    centroid_lat=region.centroid_lat,
                    centroid_lon=region.centroid_lon,
                    score_total=total,
                    score_climate=snapshot.score_climate,
                    score_air=snapshot.score_air,
                    score_safety=snapshot.score_safety,
                    score_demographics=snapshot.score_demographics,
                    score_amenities=snapshot.score_amenities,
                    score_landuse=snapshot.score_landuse,
                    score_oepnv=snapshot.score_oepnv,
                    reason=build_reason(category_scores, preferences),
                )
            )

        items.sort(key=lambda item: item.score_total, reverse=True)
        if not include_ars:
            items = items[:limit]
        if not include_details:
            return RecommendationResponse(items=items)
        for item in items:
            row = next(region for region, _ in rows if region.ars == item.ars)
            category_scores = {
                "climate": item.score_climate,
                "air": item.score_air,
                "safety": item.score_safety,
                "demographics": item.score_demographics,
                "amenities": item.score_amenities,
                "landuse": item.score_landuse,
                "oepnv": item.score_oepnv,
            }
            score_formula, calculation_details, indicators = self.build_region_explanation(
                ars=row.ars,
                region_id=row.id,
                region_level=row.level,
                region_population=row.population,
                category_scores=category_scores,
                preferences=preferences,
            )
            item.score_formula = score_formula
            item.calculation_details = calculation_details
            item.indicators = indicators
        return RecommendationResponse(items=items)

    def get_top_rankings(
        self,
        *,
        state_code: str | None,
        category: str,
        limit: int = 100,
    ) -> RecommendationResponse:
        preferences = self.preferences_for_category(category, state_code)
        rows = self.repository.list_top_snapshots_by_category(
            category=category,
            state_code=state_code,
            limit=limit,
        )
        items: list[RecommendationItem] = []
        for region, snapshot in rows:
            category_scores = {
                "climate": snapshot.score_climate,
                "air": snapshot.score_air,
                "safety": snapshot.score_safety,
                "demographics": snapshot.score_demographics,
                "amenities": snapshot.score_amenities,
                "landuse": snapshot.score_landuse,
                "oepnv": snapshot.score_oepnv,
            }
            items.append(
                RecommendationItem(
                    ars=region.ars,
                    slug=slugify_region_name(region.name),
                    name=region.name,
                    level=region.level,
                    state_name=region.state_name,
                    district_name=self._district_name_for_region(region.ars, region.level, region.district_name),
                    centroid_lat=region.centroid_lat,
                    centroid_lon=region.centroid_lon,
                    score_total=snapshot.score_total,
                    score_climate=snapshot.score_climate,
                    score_air=snapshot.score_air,
                    score_safety=snapshot.score_safety,
                    score_demographics=snapshot.score_demographics,
                    score_amenities=snapshot.score_amenities,
                    score_landuse=snapshot.score_landuse,
                    score_oepnv=snapshot.score_oepnv,
                    reason=build_reason(category_scores, preferences),
                )
            )
        return RecommendationResponse(items=items)

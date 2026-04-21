from sqlmodel import Session

from app.models.preference import UserPreferenceSession
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
    "oepnv_departures_total": "Angebotsmasse",
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

    @staticmethod
    def amenity_label(category: str) -> str:
        return AMENITY_LABELS.get(category, category)

    @staticmethod
    def _effective_weight_keys(
        weights: dict[str, int],
        coverage: dict[str, float] | None = None,
    ) -> list[str]:
        weighted_keys = [key for key, weight in weights.items() if weight > 0]
        if coverage is None:
            return weighted_keys

        covered_keys = [
            key for key in weighted_keys if coverage.get(key, 0.0) > 0]
        return covered_keys or weighted_keys

    @staticmethod
    def weighted_total(
        category_scores: dict[str, float],
        preferences: RecommendationInput,
        coverage: dict[str, float] | None = None,
    ) -> float:
        weights = {
            "climate": preferences.climate_weight,
            "air": preferences.air_weight,
            "safety": preferences.safety_weight,
            "demographics": preferences.demographics_weight,
            "amenities": preferences.amenities_weight,
            "landuse": preferences.landuse_weight,
            "oepnv": preferences.oepnv_weight,
        }
        effective_keys = ScoringService._effective_weight_keys(
            weights, coverage)
        denominator = sum(weights[key] for key in effective_keys)
        if denominator == 0:
            return 0.0
        numerator = sum(
            category_scores[key] * weights[key] for key in effective_keys
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
        """Persist user preference session for analytics.

        Note: This is disabled by default for privacy reasons. Enable only if you have
        a clear purpose and retention policy documented.
        """
        # Check if persistence is enabled via environment variable
        import os
        if os.environ.get("ENABLE_PREFERENCE_PERSISTENCE", "false").lower() != "true":
            return

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

        # Optional: Clean up old sessions (retention policy: 30 days)
        self._cleanup_old_sessions(days=30)

    def _cleanup_old_sessions(self, days: int = 30) -> None:
        """Clean up user preference sessions older than specified days."""
        from datetime import datetime, timedelta
        from sqlalchemy import delete

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Note: This assumes UserPreferenceSession has a created_at field
        # If not, we should add one in a migration
        try:
            from app.models.preference import UserPreferenceSession
            stmt = delete(UserPreferenceSession).where(
                UserPreferenceSession.created_at < cutoff_date
            )
            self.session.execute(stmt)
            self.session.commit()
        except Exception as e:
            # Log but don't fail if cleanup doesn't work
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to cleanup old preference sessions: {e}")

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

    def _indicator_text(self, key: str, raw_value: float, normalized_value: float, unit: str) -> str:
        label = self.localized_indicator_name(key)
        formatted = self._format_value(raw_value, unit)
        localized_unit = self.localized_unit(unit)
        return f"{label}: Rohwert {formatted} ({localized_unit}), normierter Teil-Score {normalized_value:.1f} von 100."

    def _build_indicator_details(
        self,
        indicator_rows: list[tuple[object, object]],
    ) -> list[RecommendationIndicatorDetail]:
        details: list[RecommendationIndicatorDetail] = []
        for definition, value in indicator_rows:
            details.append(
                RecommendationIndicatorDetail(
                    key=definition.key,
                    name=self.localized_indicator_name(
                        definition.key, definition.name),
                    category=definition.category,
                    unit=definition.unit,
                    raw_value=value.raw_value,
                    normalized_value=value.normalized_value,
                    quality_flag=self.localized_quality_flag(
                        value.quality_flag),
                    source_name=definition.source_name,
                    updated_at=value.updated_at.isoformat() if value.updated_at else None,
                    text=self._indicator_text(
                        definition.key,
                        value.raw_value,
                        value.normalized_value,
                        definition.unit,
                    ),
                )
            )
        return details

    def build_category_quality_summary(
        self,
        indicator_rows: list[tuple[object, object]],
    ) -> dict[str, dict[str, object]]:
        grouped_flags: dict[str, dict[str, list[str]]] = {}

        for definition, value in indicator_rows:
            if value.quality_flag == "ok":
                continue
            category = str(definition.category)
            flag = str(value.quality_flag)
            grouped_flags.setdefault(category, {}).setdefault(flag, []).append(
                self.localized_indicator_name(definition.key, definition.name)
            )

        summary: dict[str, dict[str, object]] = {}
        for category, flags in grouped_flags.items():
            notes: list[str] = []
            for flag, indicators in sorted(flags.items()):
                localized_flag = self.localized_quality_flag(flag)
                indicator_list = ", ".join(sorted(indicators))
                notes.append(f"{localized_flag}: {indicator_list}.")
            summary[category] = {
                "status": "attention",
                "notes": notes,
            }

        return summary

    def build_category_freshness_summary(
        self,
        indicator_rows: list[tuple[object, object]],
    ) -> dict[str, dict[str, object]]:
        freshness: dict[str, dict[str, object]] = {}

        for definition, value in indicator_rows:
            category = str(definition.category)
            bucket = freshness.setdefault(
                category,
                {"updated_at": None, "sources": set()},
            )
            if value.updated_at and (
                bucket["updated_at"] is None or value.updated_at > bucket["updated_at"]
            ):
                bucket["updated_at"] = value.updated_at
            if definition.source_name:
                bucket["sources"].add(str(definition.source_name))

        return {
            category: {
                "updated_at": values["updated_at"].isoformat() if values["updated_at"] else None,
                "sources": sorted(values["sources"]),
            }
            for category, values in freshness.items()
        }

    def _build_calculation_details(
        self,
        *,
        ars: str,
        region_level: str,
        region_population: int | None,
        category_scores: dict[str, float],
        preferences: RecommendationInput,
        indicators: list[RecommendationIndicatorDetail],
        coverage: dict[str, float],
    ) -> tuple[str, list[str]]:
        weights = self._weights(preferences)
        effective_keys = self._effective_weight_keys(weights, coverage)
        denominator = sum(weights[key] for key in effective_keys)
        if denominator == 0:
            return "Keine gewichtete Kategorie hat aktuell Daten, deshalb ist der Gesamtscore 0.", [
                "Alle gewichteten Kategorien haben derzeit eine Datenabdeckung von 0 oder wurden auf 0 gewichtet."
            ]

        formula_parts = [
            f"{CATEGORY_LABELS[key]} {category_scores[key]:.1f} x {weight}"
            for key, weight in weights.items()
            if key in effective_keys
        ]
        score_formula = f"Gesamtscore = ({' + '.join(formula_parts)}) / {denominator}"

        details = [
            (
                f"{CATEGORY_LABELS[key]} trägt mit Gewicht {weight}/{denominator} bei: "
                f"{category_scores[key]:.1f} x {weight} / {denominator} = "
                f"{(category_scores[key] * weight / denominator):.1f} Punkte."
            )
            for key, weight in weights.items()
            if key in effective_keys
        ]

        has_any_coverage = any(coverage.get(key, 0.0) > 0 for key in weights)
        for key, weight in weights.items():
            if has_any_coverage and weight > 0 and coverage.get(key, 0.0) <= 0:
                details.append(
                    f"{CATEGORY_LABELS[key]} ist aktuell nicht in den Gesamtscore eingeflossen, "
                    "weil für diese Kategorie keine Datenabdeckung vorliegt."
                )

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
                details.append(
                    f"Einwohner laut Gemeindedatensatz: {self._format_value(population_value, 'count')}.")
            elif region_population is not None:
                details.append(
                    f"Einwohner laut Regionsdatensatz: {self._format_value(population_value, 'count')}.")
            else:
                details.append(
                    f"Einwohner laut Destatis-Indikator: {self._format_value(population_value, 'count')}.")
        if female_share:
            label = "Frauenanteil laut Destatis-Indikator"
            details.append(
                f"{label}: {self._format_value(female_share.raw_value, female_share.unit)}.")
        if youth_share:
            label = "Anteil unter 18 Jahren laut Destatis-Indikator"
            details.append(
                f"{label}: {self._format_value(youth_share.raw_value, youth_share.unit)}.")
        if senior_share:
            label = "Anteil ab 65 Jahren laut Destatis-Indikator"
            details.append(
                f"{label}: {self._format_value(senior_share.raw_value, senior_share.unit)}.")

        amenities = by_key.get("amenities_density")
        if amenities:
            amenity_rows = self.repository.list_amenity_aggregates(ars)
            if amenity_rows:
                amenity_parts = [
                    f"{ScoringService.amenity_label(category)}: {count_total} gesamt, {per_10k:.2f} je 10.000 Einwohner"
                    for category, count_total, per_10k in amenity_rows
                ]
                details.append("OSM-Alltagsnähe nach Kategorien: " +
                               "; ".join(amenity_parts) + ".")
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
        coverage: dict[str, float],
        preferences: RecommendationInput,
    ) -> tuple[str, list[str], list[RecommendationIndicatorDetail]]:
        indicators = self._build_indicator_details(
            self.repository.list_indicator_values(region_id)
        )
        score_formula, calculation_details = self._build_calculation_details(
            ars=ars,
            region_level=region_level,
            region_population=region_population,
            category_scores=category_scores,
            preferences=preferences,
            indicators=indicators,
            coverage=coverage,
        )
        return score_formula, calculation_details, indicators

    def get_recommendations(
        self,
        preferences: RecommendationInput,
        include_ars: list[str] | None = None,
        limit: int = 10,
        include_details: bool = True,
        persist_session: bool = False,
    ) -> RecommendationResponse:
        if persist_session:
            self._persist_preference_session(preferences)
        weights = self._weights(preferences)
        if include_ars:
            rows = self.repository.list_snapshots(
                include_ars=include_ars,
                state_code=preferences.state_code,
            )
        else:
            rows = self.repository.list_ranked_snapshots_by_preferences(
                weights=weights,
                state_code=preferences.state_code,
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
            coverage = {
                "climate": snapshot.coverage_climate,
                "air": snapshot.coverage_air,
                "safety": snapshot.coverage_safety,
                "demographics": snapshot.coverage_demographics,
                "amenities": snapshot.coverage_amenities,
                "landuse": snapshot.coverage_landuse,
                "oepnv": snapshot.coverage_oepnv,
            }
            total = self.weighted_total(category_scores, preferences, coverage)
            items.append(
                RecommendationItem(
                    ars=region.ars,
                    slug=region.slug or region.ars,
                    name=region.name,
                    level=region.level,
                    state_name=region.state_name,
                    district_name=region.district_name,
                    centroid_lat=region.centroid_lat,
                    centroid_lon=region.centroid_lon,
                    score_total=snapshot.score_total,
                    score_profile=total,
                    score_climate=snapshot.score_climate,
                    score_air=snapshot.score_air,
                    score_safety=snapshot.score_safety,
                    score_demographics=snapshot.score_demographics,
                    score_amenities=snapshot.score_amenities,
                    score_landuse=snapshot.score_landuse,
                    score_oepnv=snapshot.score_oepnv,
                    coverage_climate=snapshot.coverage_climate,
                    coverage_air=snapshot.coverage_air,
                    coverage_safety=snapshot.coverage_safety,
                    coverage_demographics=snapshot.coverage_demographics,
                    coverage_amenities=snapshot.coverage_amenities,
                    coverage_landuse=snapshot.coverage_landuse,
                    coverage_oepnv=snapshot.coverage_oepnv,
                    reason=build_reason(category_scores, preferences),
                )
            )

        if include_ars:
            items.sort(key=lambda item: item.score_profile, reverse=True)
        else:
            items = items[:limit]
        if not include_details:
            return RecommendationResponse(items=items)

        item_by_ars = {item.ars: item for item in items}
        region_by_ars = {region.ars: region for region,
                         _ in rows if region.ars in item_by_ars}
        indicator_rows_by_region = self.repository.list_indicator_values_for_regions(
            [region.id for region in region_by_ars.values() if region.id is not None]
        )

        for item in items:
            row = region_by_ars[item.ars]
            category_scores = {
                "climate": item.score_climate,
                "air": item.score_air,
                "safety": item.score_safety,
                "demographics": item.score_demographics,
                "amenities": item.score_amenities,
                "landuse": item.score_landuse,
                "oepnv": item.score_oepnv,
            }
            coverage = {
                "climate": item.coverage_climate,
                "air": item.coverage_air,
                "safety": item.coverage_safety,
                "demographics": item.coverage_demographics,
                "amenities": item.coverage_amenities,
                "landuse": item.coverage_landuse,
                "oepnv": item.coverage_oepnv,
            }
            indicators = self._build_indicator_details(
                indicator_rows_by_region.get(int(row.id), [])
            )
            score_formula, calculation_details = self._build_calculation_details(
                ars=row.ars,
                region_level=row.level,
                region_population=row.population,
                category_scores=category_scores,
                preferences=preferences,
                indicators=indicators,
                coverage=coverage,
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
                    slug=region.slug or region.ars,
                    name=region.name,
                    level=region.level,
                    state_name=region.state_name,
                    district_name=region.district_name,
                    centroid_lat=region.centroid_lat,
                    centroid_lon=region.centroid_lon,
                    score_total=snapshot.score_total,
                    score_profile=snapshot.score_total,
                    score_climate=snapshot.score_climate,
                    score_air=snapshot.score_air,
                    score_safety=snapshot.score_safety,
                    score_demographics=snapshot.score_demographics,
                    score_amenities=snapshot.score_amenities,
                    score_landuse=snapshot.score_landuse,
                    score_oepnv=snapshot.score_oepnv,
                    coverage_climate=snapshot.coverage_climate,
                    coverage_air=snapshot.coverage_air,
                    coverage_safety=snapshot.coverage_safety,
                    coverage_demographics=snapshot.coverage_demographics,
                    coverage_amenities=snapshot.coverage_amenities,
                    coverage_landuse=snapshot.coverage_landuse,
                    coverage_oepnv=snapshot.coverage_oepnv,
                    trust_updated_at=snapshot.updated_at.isoformat() if snapshot.updated_at else None,
                    reason=build_reason(category_scores, preferences),
                )
            )

        region_by_ars = {region.ars: region for region, _ in rows}
        indicator_rows_by_region = self.repository.list_indicator_values_for_regions(
            [region.id for region in region_by_ars.values() if region.id is not None]
        )

        for item in items:
            region = region_by_ars[item.ars]
            indicator_rows = indicator_rows_by_region.get(int(region.id), [])
            freshness_by_category = self.build_category_freshness_summary(
                indicator_rows)
            quality_by_category = self.build_category_quality_summary(
                indicator_rows)
            freshness = freshness_by_category.get(category, {})
            quality = quality_by_category.get(category, {})
            if freshness.get("updated_at"):
                item.trust_updated_at = str(freshness["updated_at"])
            if freshness.get("sources"):
                item.trust_sources = list(freshness["sources"])
            if quality.get("notes"):
                item.trust_quality_notes = list(quality["notes"])
        return RecommendationResponse(items=items)

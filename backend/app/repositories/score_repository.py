from math import log

from sqlalchemy import case, desc, func, literal, text
from sqlmodel import Session, select

from app.core.ars import lookup_candidates
from app.core.config import settings
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot

CATEGORY_SCORE_COLUMNS = {
    "climate": "score_climate",
    "air": "score_air",
    "safety": "score_safety",
    "demographics": "score_demographics",
    "amenities": "score_amenities",
    "landuse": "score_landuse",
    "oepnv": "score_oepnv",
}

URBANITY_BLEND_WEIGHT = 0.2
URBANITY_POPULATION_FLOOR = 10_000
URBANITY_POPULATION_CEILING = 250_000


class ScoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_indicators(self) -> list[IndicatorDefinition]:
        statement = select(IndicatorDefinition).order_by(
            IndicatorDefinition.category, IndicatorDefinition.key
        )
        return list(self.session.exec(statement))

    def list_snapshots(
        self,
        include_ars: list[str] | None = None,
        state_code: str | None = None,
    ) -> list[tuple[Region, RegionScoreSnapshot]]:
        statement = (
            select(Region, RegionScoreSnapshot)
            .join(RegionScoreSnapshot, Region.id == RegionScoreSnapshot.region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
        )
        if include_ars:
            candidates: set[str] = set()
            for item in include_ars:
                candidates.update(lookup_candidates(item))
            statement = statement.where(Region.ars.in_(list(candidates)))
        if state_code:
            statement = statement.where(Region.state_code == state_code)
        return list(self.session.exec(statement).all())

    def list_indicator_values(
        self, region_id: int
    ) -> list[tuple[IndicatorDefinition, RegionIndicatorValue]]:
        statement = (
            select(IndicatorDefinition, RegionIndicatorValue)
            .join(RegionIndicatorValue, RegionIndicatorValue.indicator_id == IndicatorDefinition.id)
            .where(RegionIndicatorValue.region_id == region_id)
            .where(RegionIndicatorValue.period == settings.default_score_period)
            .order_by(IndicatorDefinition.category, IndicatorDefinition.key)
        )
        return list(self.session.exec(statement).all())

    def list_indicator_values_for_regions(
        self, region_ids: list[int]
    ) -> dict[int, list[tuple[IndicatorDefinition, RegionIndicatorValue]]]:
        if not region_ids:
            return {}
        statement = (
            select(IndicatorDefinition, RegionIndicatorValue)
            .join(RegionIndicatorValue, RegionIndicatorValue.indicator_id == IndicatorDefinition.id)
            .where(RegionIndicatorValue.region_id.in_(region_ids))
            .where(RegionIndicatorValue.period == settings.default_score_period)
            .order_by(
                RegionIndicatorValue.region_id,
                IndicatorDefinition.category,
                IndicatorDefinition.key,
            )
        )
        grouped: dict[int, list[tuple[IndicatorDefinition, RegionIndicatorValue]]] = {
            region_id: [] for region_id in region_ids
        }
        for definition, value in self.session.exec(statement).all():
            grouped.setdefault(int(value.region_id), []).append((definition, value))
        return grouped

    def list_ranked_snapshots_by_preferences(
        self,
        *,
        weights: dict[str, int],
        state_code: str | None = None,
        min_scores: dict[str, float | None] | None = None,
        coverage_min: float | None = None,
        urbanity_boost: bool = False,
        limit: int = 10,
    ) -> list[tuple[Region, RegionScoreSnapshot]]:
        score_columns = {
            "climate": RegionScoreSnapshot.score_climate,
            "air": RegionScoreSnapshot.score_air,
            "safety": RegionScoreSnapshot.score_safety,
            "demographics": RegionScoreSnapshot.score_demographics,
            "amenities": RegionScoreSnapshot.score_amenities,
            "landuse": RegionScoreSnapshot.score_landuse,
            "oepnv": RegionScoreSnapshot.score_oepnv,
        }
        coverage_columns = {
            "climate": RegionScoreSnapshot.coverage_climate,
            "air": RegionScoreSnapshot.coverage_air,
            "safety": RegionScoreSnapshot.coverage_safety,
            "demographics": RegionScoreSnapshot.coverage_demographics,
            "amenities": RegionScoreSnapshot.coverage_amenities,
            "landuse": RegionScoreSnapshot.coverage_landuse,
            "oepnv": RegionScoreSnapshot.coverage_oepnv,
        }

        weighted_numerator = literal(0.0)
        weighted_denominator = literal(0.0)
        fallback_numerator = literal(0.0)
        fallback_denominator = literal(0.0)

        for category, weight in weights.items():
            if weight <= 0:
                continue
            score_column = score_columns[category]
            coverage_column = coverage_columns[category]
            weight_literal = literal(float(weight))
            coverage_weight = case((coverage_column > 0, coverage_column), else_=0.0)
            weighted_numerator = weighted_numerator + (
                score_column * weight_literal * coverage_weight
            )
            weighted_denominator = weighted_denominator + (weight_literal * coverage_weight)
            fallback_numerator = fallback_numerator + (score_column * weight_literal)
            fallback_denominator = fallback_denominator + weight_literal

        profile_score = case(
            (weighted_denominator > 0, weighted_numerator / weighted_denominator),
            (fallback_denominator > 0, fallback_numerator / fallback_denominator),
            else_=literal(0.0),
        )
        coverage_confidence = case(
            (fallback_denominator > 0, weighted_denominator / fallback_denominator),
            else_=literal(0.0),
        )
        profile_score = profile_score * coverage_confidence
        if urbanity_boost:
            population = func.coalesce(Region.population, 0)
            log_floor = log(URBANITY_POPULATION_FLOOR)
            log_range = log(URBANITY_POPULATION_CEILING) - log_floor
            urbanity_score = case(
                (population <= URBANITY_POPULATION_FLOOR, literal(0.0)),
                (population >= URBANITY_POPULATION_CEILING, literal(100.0)),
                else_=((func.ln(population) - literal(log_floor)) / literal(log_range))
                * literal(100.0),
            )
            profile_score = (
                profile_score * literal(1.0 - URBANITY_BLEND_WEIGHT)
                + urbanity_score * literal(URBANITY_BLEND_WEIGHT)
            ) * coverage_confidence

        statement = (
            select(Region, RegionScoreSnapshot)
            .join(RegionScoreSnapshot, Region.id == RegionScoreSnapshot.region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
        )
        if state_code:
            statement = statement.where(Region.state_code == state_code)
        if min_scores:
            for category, minimum in min_scores.items():
                if minimum is None:
                    continue
                statement = statement.where(score_columns[category] >= minimum)
        if coverage_min is not None:
            normalized_coverage_min = coverage_min / 100
            coverage_expression = (
                RegionScoreSnapshot.coverage_climate
                + RegionScoreSnapshot.coverage_air
                + RegionScoreSnapshot.coverage_safety
                + RegionScoreSnapshot.coverage_demographics
                + RegionScoreSnapshot.coverage_amenities
                + RegionScoreSnapshot.coverage_landuse
                + RegionScoreSnapshot.coverage_oepnv
            ) / 7
            statement = statement.where(coverage_expression >= normalized_coverage_min)
        statement = statement.order_by(desc(profile_score), Region.id).limit(limit)
        return list(self.session.exec(statement).all())

    def list_top_snapshots_by_category(
        self,
        *,
        category: str,
        state_code: str | None = None,
        limit: int = 100,
    ) -> list[tuple[Region, RegionScoreSnapshot]]:
        score_column_name = CATEGORY_SCORE_COLUMNS.get(category)
        if score_column_name is None:
            raise ValueError(f"Unknown ranking category: {category}")

        score_column = getattr(RegionScoreSnapshot, score_column_name)
        statement = (
            select(Region, RegionScoreSnapshot)
            .join(RegionScoreSnapshot, Region.id == RegionScoreSnapshot.region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
            .order_by(desc(score_column), Region.id)
            .limit(limit)
        )
        if state_code:
            statement = statement.where(Region.state_code == state_code)
        return list(self.session.exec(statement).all())

    def list_amenity_aggregates(self, ars: str) -> list[tuple[str, int, float]]:
        table_exists = self.session.execute(
            text("SELECT to_regclass('osm.region_amenity_agg') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return []

        rows = self.session.execute(
            text(
                """
                SELECT category, count_total, per_10k::float
                FROM osm.region_amenity_agg
                WHERE ars = :ars
                ORDER BY category
                """
            ),
            {"ars": ars},
        ).all()
        return [(str(row[0]), int(row[1]), float(row[2])) for row in rows]

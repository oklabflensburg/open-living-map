from sqlalchemy import text
from sqlmodel import Session, select

from app.core.ars import lookup_candidates
from app.core.config import settings
from app.models.indicator import IndicatorDefinition
from app.models.indicator import RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot


class ScoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_indicators(self) -> list[IndicatorDefinition]:
        statement = select(IndicatorDefinition).order_by(IndicatorDefinition.category, IndicatorDefinition.key)
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

    def list_indicator_values(self, region_id: int) -> list[tuple[IndicatorDefinition, RegionIndicatorValue]]:
        statement = (
            select(IndicatorDefinition, RegionIndicatorValue)
            .join(RegionIndicatorValue, RegionIndicatorValue.indicator_id == IndicatorDefinition.id)
            .where(RegionIndicatorValue.region_id == region_id)
            .where(RegionIndicatorValue.period == settings.default_score_period)
            .order_by(IndicatorDefinition.category, IndicatorDefinition.key)
        )
        return list(self.session.exec(statement).all())

    def list_amenity_aggregates(self, ars: str) -> list[tuple[str, int, float]]:
        table_exists = self.session.execute(text("SELECT to_regclass('osm.region_amenity_agg') IS NOT NULL")).scalar()
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

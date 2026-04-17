import logging
from collections import defaultdict

from sqlmodel import select

from app.core.config import settings
from app.etl.common import with_session
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot

logger = logging.getLogger("etl.build_scores")
logging.basicConfig(level=logging.INFO)

CATEGORIES = ["climate", "air", "safety", "demographics", "amenities", "oepnv"]


def main() -> None:
    logger.info("Score-Build gestartet")
    with with_session() as session:
        regions = list(session.exec(select(Region)))
        indicators = {row.id: row for row in session.exec(select(IndicatorDefinition))}

        for region in regions:
            values = list(
                session.exec(
                    select(RegionIndicatorValue).where(
                        RegionIndicatorValue.region_id == region.id,
                        RegionIndicatorValue.period == settings.default_score_period,
                    )
                )
            )

            bucket: dict[str, list[float]] = defaultdict(list)
            for value in values:
                indicator = indicators.get(value.indicator_id)
                if not indicator:
                    continue
                bucket[indicator.category].append(value.normalized_value)

            category_scores: dict[str, float] = {}
            for category in CATEGORIES:
                entries = bucket.get(category, [])
                category_scores[category] = round(sum(entries) / len(entries), 2) if entries else 0.0

            total = round(sum(category_scores.values()) / len(CATEGORIES), 2)
            explanation = {
                "summary": "Teil-Scores wurden als Mittelwert der normierten Indikatoren je Kategorie berechnet.",
                "categories": category_scores,
            }

            existing = session.exec(
                select(RegionScoreSnapshot).where(
                    RegionScoreSnapshot.region_id == region.id,
                    RegionScoreSnapshot.profile_key == "base",
                    RegionScoreSnapshot.period == settings.default_score_period,
                )
            ).first()

            if existing:
                existing.score_total = total
                existing.score_climate = category_scores["climate"]
                existing.score_air = category_scores["air"]
                existing.score_safety = category_scores["safety"]
                existing.score_demographics = category_scores["demographics"]
                existing.score_amenities = category_scores["amenities"]
                existing.score_oepnv = category_scores["oepnv"]
                existing.explanation_json = explanation
                session.add(existing)
            else:
                session.add(
                    RegionScoreSnapshot(
                        region_id=region.id,
                        profile_key="base",
                        period=settings.default_score_period,
                        score_total=total,
                        score_climate=category_scores["climate"],
                        score_air=category_scores["air"],
                        score_safety=category_scores["safety"],
                        score_demographics=category_scores["demographics"],
                        score_amenities=category_scores["amenities"],
                        score_oepnv=category_scores["oepnv"],
                        explanation_json=explanation,
                    )
                )

        session.commit()
    logger.info("Score-Build abgeschlossen")


if __name__ == "__main__":
    main()

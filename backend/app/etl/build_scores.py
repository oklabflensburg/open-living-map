import logging
from collections import defaultdict

from sqlmodel import select

from app.core.config import settings
from app.etl.common import tracked_etl_run, with_session
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot

logger = logging.getLogger("etl.build_scores")
logging.basicConfig(level=logging.INFO)

CATEGORIES = ["climate", "air", "safety", "demographics", "amenities", "landuse", "oepnv"]

INDICATOR_WEIGHTS = {
    "oepnv": {
        "oepnv_departures_per_10k": 0.4,
        "oepnv_stop_density": 0.25,
        "oepnv_departures_total": 0.2,
        "oepnv_departure_regularity": 0.15,
    }
}


def _category_score(
    category: str,
    entries: list[tuple[IndicatorDefinition, float]],
) -> float | None:
    if not entries:
        return None

    weights = INDICATOR_WEIGHTS.get(category)
    if not weights:
        return round(sum(value for _, value in entries) / len(entries), 2)

    weighted_entries = [
        (value, weights.get(indicator.key, 1.0))
        for indicator, value in entries
    ]
    denominator = sum(weight for _, weight in weighted_entries)
    if denominator <= 0:
        return round(sum(value for value, _ in weighted_entries) / len(weighted_entries), 2)
    return round(
        sum(value * weight for value, weight in weighted_entries) / denominator,
        2,
    )


def main() -> None:
    logger.info("Score-Build gestartet")
    with tracked_etl_run(job_name="build_scores") as run:
        with with_session() as session:
            regions = list(session.exec(select(Region)))
            indicators = {row.id: row for row in session.exec(select(IndicatorDefinition))}

        # Count total indicators per category for coverage calculation
            indicators_by_category: dict[str, list[IndicatorDefinition]] = defaultdict(list)
            for indicator in indicators.values():
                indicators_by_category[indicator.category].append(indicator)

            total_indicators_per_category = {
                category: len(indicators_by_category[category])
                for category in CATEGORIES
            }

            for region in regions:
                values = list(
                    session.exec(
                        select(RegionIndicatorValue).where(
                            RegionIndicatorValue.region_id == region.id,
                            RegionIndicatorValue.period == settings.default_score_period,
                        )
                    )
                )

                bucket: dict[str, list[tuple[IndicatorDefinition, float]]] = defaultdict(list)
                for value in values:
                    indicator = indicators.get(value.indicator_id)
                    if not indicator:
                        continue
                    bucket[indicator.category].append((indicator, value.normalized_value))

                category_scores: dict[str, float] = {}
                category_coverage: dict[str, float] = {}

                for category in CATEGORIES:
                    entries = bucket.get(category, [])
                    total_indicators = total_indicators_per_category[category]

                    # Calculate coverage (percentage of available indicators)
                    if total_indicators > 0:
                        coverage = len(entries) / total_indicators
                    else:
                        coverage = 0.0
                    category_coverage[category] = round(coverage, 3)  # Keep 3 decimal places for precision

                    # Calculate score only if we have data (coverage > 0)
                    if entries:
                        category_scores[category] = _category_score(category, entries)
                    else:
                        # Missing category - don't assign a score
                        category_scores[category] = None

                # Calculate total score with a coverage penalty so sparse proxy data
                # cannot rank like a fully covered region.
                categories_with_data = [cat for cat in CATEGORIES if category_scores[cat] is not None]
                if categories_with_data:
                    total = round(
                        sum(
                            (category_scores[cat] or 0.0) * category_coverage[cat]
                            for cat in CATEGORIES
                        ) / len(CATEGORIES),
                        2
                    )
                else:
                    total = 0.0

                explanation = {
                    "summary": "Teil-Scores wurden als Mittelwert der normierten Indikatoren je Kategorie berechnet.",
                    "categories": category_scores,
                    "coverage": category_coverage,
                    "categories_with_data": categories_with_data,
                    "total_categories_considered": len(categories_with_data),
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
                    existing.score_climate = category_scores["climate"] or 0.0
                    existing.score_air = category_scores["air"] or 0.0
                    existing.score_safety = category_scores["safety"] or 0.0
                    existing.score_demographics = category_scores["demographics"] or 0.0
                    existing.score_amenities = category_scores["amenities"] or 0.0
                    existing.score_landuse = category_scores["landuse"] or 0.0
                    existing.score_oepnv = category_scores["oepnv"] or 0.0
                    existing.coverage_climate = category_coverage["climate"]
                    existing.coverage_air = category_coverage["air"]
                    existing.coverage_safety = category_coverage["safety"]
                    existing.coverage_demographics = category_coverage["demographics"]
                    existing.coverage_amenities = category_coverage["amenities"]
                    existing.coverage_landuse = category_coverage["landuse"]
                    existing.coverage_oepnv = category_coverage["oepnv"]
                    existing.explanation_json = explanation
                    session.add(existing)
                else:
                    session.add(
                        RegionScoreSnapshot(
                            region_id=region.id,
                            profile_key="base",
                            period=settings.default_score_period,
                            score_total=total,
                            score_climate=category_scores["climate"] or 0.0,
                            score_air=category_scores["air"] or 0.0,
                            score_safety=category_scores["safety"] or 0.0,
                            score_demographics=category_scores["demographics"] or 0.0,
                            score_amenities=category_scores["amenities"] or 0.0,
                            score_landuse=category_scores["landuse"] or 0.0,
                            score_oepnv=category_scores["oepnv"] or 0.0,
                            coverage_climate=category_coverage["climate"],
                            coverage_air=category_coverage["air"],
                            coverage_safety=category_coverage["safety"],
                            coverage_demographics=category_coverage["demographics"],
                            coverage_amenities=category_coverage["amenities"],
                            coverage_landuse=category_coverage["landuse"],
                            coverage_oepnv=category_coverage["oepnv"],
                            explanation_json=explanation,
                        )
                    )

            session.commit()
            run.set_rows_written(len(regions))
        logger.info("Score-Build abgeschlossen")


if __name__ == "__main__":
    main()

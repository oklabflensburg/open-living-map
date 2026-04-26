import json
import re
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.ars import lookup_candidates, slugify_region_name
from app.core.config import settings
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot

MANDATORY_SOURCE_LINKS = [
    "https://www.opendata-oepnv.de/ht/de/datensaetze",
    "https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:ags",
    "https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:kreis",
]

AMENITY_CATEGORY_MAPPING = {
    "pharmacy": [("amenity", "pharmacy")],
    "doctors": [("amenity", "doctors")],
    "hospital": [("amenity", "hospital")],
    "childcare": [("amenity", "kindergarten")],
    "school": [("amenity", "school")],
    "supermarket": [("shop", "supermarket")],
    "station": [("railway", "station")],
    "transit_stop": [("highway", "bus_stop")],
    "playground": [("leisure", "playground")],
    "park": [("leisure", "park")],
    "museum": [("tourism", "museum")],
    "theatre": [("amenity", "theatre")],
    "sports_facility": [
        ("leisure", "sports_centre"),
        ("leisure", "stadium"),
        ("leisure", "swimming_pool"),
        ("sport", "swimming"),
    ],
    "theme_park": [("tourism", "zoo"), ("tourism", "theme_park")],
    "nature_reserve": [("leisure", "nature_reserve"), ("boundary", "protected_area")],
    "airfield": [("aeroway", "aerodrome")],
    "restaurant": [
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
        ("amenity", "bar"),
        ("amenity", "pub"),
        ("amenity", "fast_food"),
    ],
    "library": [("amenity", "library")],
}

ACCIDENT_CATEGORY_ORDER = [
    "killed",
    "seriously_injured",
    "slightly_injured",
]

ACCIDENT_CATEGORY_LABELS = {
    "killed": "Getötete",
    "seriously_injured": "Schwerverletzte",
    "slightly_injured": "Leichtverletzte",
}


def _build_tag_match_condition(
    alias: str, mappings: list[tuple[str, str]]
) -> tuple[str, dict[str, str]]:
    clauses: list[str] = []
    params: dict[str, str] = {}
    for index, (osm_key, osm_value) in enumerate(mappings):
        key_param = f"{alias}_osm_key_{index}"
        value_param = f"{alias}_osm_value_{index}"
        clauses.append(
            f'COALESCE({alias}."{osm_key}", {alias}.tags -> CAST(:{key_param} AS text)) = CAST(:{value_param} AS text)'
        )
        params[key_param] = osm_key
        params[value_param] = osm_value
    return "(" + " OR ".join(clauses) + ")", params


class RegionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _search_region_ars(
        self,
        search_query: str,
        limit: int,
        offset: int,
        state_code: str | None = None,
    ) -> list[str]:
        query = search_query.strip().lower()
        raw_query = search_query.strip()
        contains_pattern = f"%{query}%"
        prefix_pattern = f"{query}%"
        postal_prefix = f"{raw_query}%"
        state_filter = "AND r.state_code = :state_code" if state_code else ""
        is_exact_postal = bool(re.fullmatch(r"\d{5}", raw_query))
        is_numeric_query = raw_query.isdigit()

        if is_exact_postal:
            rows = self.session.execute(
                text(
                    f"""
                    SELECT r.ars
                    FROM region r
                    JOIN postal.region_postal_code pc ON pc.region_ars = r.ars
                    WHERE pc.postal_code = :raw_query
                      AND pc.is_primary = true
                      {state_filter}
                    ORDER BY pc.overlap_area DESC NULLS LAST, COALESCE(r.population, 0) DESC, r.name
                    LIMIT :limit
                    OFFSET :offset
                    """
                ),
                {
                    "raw_query": raw_query,
                    "limit": limit,
                    "offset": offset,
                    **({"state_code": state_code} if state_code else {}),
                },
            ).all()
            if rows:
                return [str(row[0]) for row in rows]

        if not is_numeric_query:
            rows = self.session.execute(
                text(
                    f"""
                    SELECT r.ars
                    FROM region r
                    WHERE (
                           lower(r.name) LIKE :contains_pattern
                       OR lower(r.state_name) LIKE :contains_pattern
                    )
                      {state_filter}
                    ORDER BY
                        CASE
                            WHEN lower(r.name) = :query THEN 0
                            WHEN lower(r.name) LIKE :prefix_pattern THEN 1
                            WHEN lower(r.state_name) = :query THEN 2
                            WHEN lower(r.state_name) LIKE :prefix_pattern THEN 3
                            ELSE 4
                        END,
                        GREATEST(
                            similarity(lower(r.name), :query),
                            similarity(lower(r.state_name), :query)
                        ) DESC,
                        char_length(r.name),
                        r.name
                    LIMIT :limit
                    OFFSET :offset
                    """
                ),
                {
                    "query": query,
                    "contains_pattern": contains_pattern,
                    "prefix_pattern": prefix_pattern,
                    "limit": limit,
                    "offset": offset,
                    **({"state_code": state_code} if state_code else {}),
                },
            ).all()
            return [str(row[0]) for row in rows]

        rows = self.session.execute(
            text(
                f"""
                SELECT r.ars
                FROM region r
                WHERE (
                       lower(r.name) LIKE :contains_pattern
                   OR lower(r.state_name) LIKE :contains_pattern
                   OR r.ars LIKE :ars_prefix
                   OR EXISTS (
                        SELECT 1
                        FROM postal.region_postal_code pc
                        WHERE pc.region_ars = r.ars
                          AND pc.postal_code LIKE :postal_prefix
                   )
                )
                  {state_filter}
                ORDER BY
                    CASE
                        WHEN r.ars = :raw_query THEN 0
                        WHEN EXISTS (
                            SELECT 1
                            FROM postal.region_postal_code pc
                            WHERE pc.region_ars = r.ars
                              AND pc.postal_code = :raw_query
                        ) THEN 1
                        WHEN lower(r.name) = :query THEN 2
                        WHEN lower(r.name) LIKE :prefix_pattern THEN 3
                        WHEN EXISTS (
                            SELECT 1
                            FROM postal.region_postal_code pc
                            WHERE pc.region_ars = r.ars
                              AND pc.postal_code LIKE :postal_prefix
                        ) THEN 4
                        WHEN lower(r.state_name) LIKE :prefix_pattern THEN 5
                        ELSE 6
                    END,
                    char_length(r.name),
                    r.name
                LIMIT :limit
                OFFSET :offset
                """
            ),
            {
                "query": query,
                "raw_query": raw_query,
                "contains_pattern": contains_pattern,
                "prefix_pattern": prefix_pattern,
                "ars_prefix": f"{raw_query}%",
                "postal_prefix": postal_prefix,
                "limit": limit,
                "offset": offset,
                **({"state_code": state_code} if state_code else {}),
            },
        ).all()
        return [str(row[0]) for row in rows]

    def list_regions(
        self,
        search_query: str | None = None,
        state_code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Region]:
        if search_query:
            ars_matches = self._search_region_ars(
                search_query,
                limit=limit,
                offset=offset,
                state_code=state_code,
            )
            if not ars_matches:
                return []
            statement = select(Region).where(Region.ars.in_(ars_matches))
            regions = list(self.session.exec(statement))
            order = {ars: index for index, ars in enumerate(ars_matches)}
            regions.sort(key=lambda region: order.get(region.ars, len(order)))
            return regions

        statement = select(Region).order_by(Region.name)
        if state_code:
            statement = statement.where(Region.state_code == state_code)
        statement = statement.offset(offset).limit(limit)
        return list(self.session.exec(statement))

    def get_by_ars(self, ars: str) -> Region | None:
        statement = select(Region).where(Region.ars.in_(lookup_candidates(ars)))
        region = self.session.exec(statement).first()
        if region:
            return region

        requested_slug = slugify_region_name(ars)
        slug_statement = select(Region).where(Region.slug == requested_slug)
        return self.session.exec(slug_statement).first()

    def get_score_snapshot(self, region_id: int) -> RegionScoreSnapshot | None:
        statement = (
            select(RegionScoreSnapshot)
            .where(RegionScoreSnapshot.region_id == region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
        )
        return self.session.exec(statement).first()

    def get_category_freshness(self, region_id: int) -> dict[str, dict[str, Any]]:
        statement = (
            select(
                IndicatorDefinition.category,
                IndicatorDefinition.source_name,
                RegionIndicatorValue.updated_at,
            )
            .join(
                RegionIndicatorValue,
                RegionIndicatorValue.indicator_id == IndicatorDefinition.id,
            )
            .where(RegionIndicatorValue.region_id == region_id)
            .where(RegionIndicatorValue.period == settings.default_score_period)
        )
        rows = self.session.exec(statement).all()

        freshness: dict[str, dict[str, Any]] = {}
        for category, source_name, updated_at in rows:
            bucket = freshness.setdefault(
                str(category),
                {"updated_at": None, "sources": set()},
            )
            if updated_at and (bucket["updated_at"] is None or updated_at > bucket["updated_at"]):
                bucket["updated_at"] = updated_at
            if source_name:
                bucket["sources"].add(str(source_name))

        return {
            category: {
                "updated_at": values["updated_at"],
                "sources": sorted(values["sources"]),
            }
            for category, values in freshness.items()
        }

    def get_boundary_geojson(self, ars: str) -> dict[str, Any] | None:
        table_exists = self.session.execute(
            text("SELECT to_regclass('geo.municipality_boundary') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return None

        row = self.session.execute(
            text(
                """
                SELECT ST_AsGeoJSON(geom)::json
                FROM geo.municipality_boundary
                WHERE ags = :ars
                LIMIT 1
                """
            ),
            {"ars": ars},
        ).first()
        if row is None or row[0] is None:
            return None
        if isinstance(row[0], str):
            return json.loads(row[0])
        return dict(row[0])

    def get_state_boundaries_geojson(self, state_code: str | None = None) -> dict[str, Any]:
        table_exists = self.session.execute(
            text("SELECT to_regclass('geo.state_boundary') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return {"type": "FeatureCollection", "features": []}

        state_filter = "WHERE state_code = :state_code" if state_code else ""
        simplify_tolerance = 250.0 if state_code else 1000.0
        params: dict[str, Any] = {
            "simplify_tolerance": simplify_tolerance,
            "geojson_precision": 5,
        }
        if state_code:
            params["state_code"] = state_code
        row = self.session.execute(
            text(
                f"""
                SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(
                                    ST_Transform(
                                        ST_SimplifyPreserveTopology(
                                            ST_Transform(geom, 3857),
                                            :simplify_tolerance
                                        ),
                                        4326
                                    ),
                                    :geojson_precision
                                )::json,
                                'properties', json_build_object(
                                    'state_code', state_code,
                                    'state_name', state_name
                                )
                            )
                            ORDER BY state_code
                        ),
                        '[]'::json
                    )
                )
                FROM geo.state_boundary
                {state_filter}
                """
            ),
            params,
        ).scalar()
        if row is None:
            return {"type": "FeatureCollection", "features": []}
        if isinstance(row, str):
            return json.loads(row)
        return dict(row)

    def list_source_links(self) -> list[str]:
        statement = (
            select(IndicatorDefinition.source_url)
            .where(IndicatorDefinition.source_url.is_not(None))
            .where(IndicatorDefinition.source_url != "")
            .distinct()
            .order_by(IndicatorDefinition.source_url)
        )
        links = list(self.session.exec(statement))
        for required in MANDATORY_SOURCE_LINKS:
            if required not in links:
                links.append(required)
        return sorted(set(links))

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

    def get_amenity_pois_geojson(self, ars: str, category: str) -> dict[str, Any] | None:
        if category not in AMENITY_CATEGORY_MAPPING:
            return None

        boundary_exists = self.session.execute(
            text("SELECT to_regclass('geo.municipality_boundary') IS NOT NULL")
        ).scalar()
        stage_exists = self.session.execute(
            text("SELECT to_regclass('osm.amenity_poi_stage') IS NOT NULL")
        ).scalar()
        if not boundary_exists or not stage_exists:
            return {
                "type": "FeatureCollection",
                "features": [],
            }

        rows = self.session.execute(
            text(
                """
                WITH boundary AS (
                    SELECT ST_Transform(geom, 3857) AS geom
                    FROM geo.municipality_boundary
                    WHERE ags = :ars
                    LIMIT 1
                )
                SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(ST_Transform(p.geom, 4326))::json,
                                'properties', json_build_object(
                                    'name', p.name,
                                    'category', CAST(:category AS text),
                                    'source_type', 'stage'
                                )
                            )
                        ),
                        '[]'::json
                    )
                )
                FROM osm.amenity_poi_stage p
                CROSS JOIN boundary b
                WHERE p.category = :category
                  AND p.geom && b.geom
                  AND ST_Covers(b.geom, p.geom)
                """
            ),
            {"ars": ars, "category": category},
        ).scalar()
        if rows is None:
            return {
                "type": "FeatureCollection",
                "features": [],
            }
        if isinstance(rows, str):
            return json.loads(rows)
        return dict(rows)

    def list_accident_stats(self, ars: str) -> list[tuple[str, int]]:
        table_exists = self.session.execute(
            text("SELECT to_regclass('traffic.accident_point') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return []
        rows = self.session.execute(
            text(
                """
                SELECT category, COUNT(*)::int AS count_total
                FROM traffic.accident_point
                WHERE region_ars = :ars
                GROUP BY category
                """
            ),
            {"ars": ars},
        ).all()
        counts = {str(row[0]): int(row[1]) for row in rows}
        return [
            (category, counts[category])
            for category in ACCIDENT_CATEGORY_ORDER
            if category in counts
        ]

    def list_air_stations(
        self, ars: str
    ) -> list[tuple[str, str, str | None, str, float | None, float | None, str | None, str]]:
        table_exists = self.session.execute(
            text("SELECT to_regclass('air.region_air_station') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return []
        rows = self.session.execute(
            text(
                """
                SELECT
                    indicator_key,
                    station_id,
                    station_code,
                    station_name,
                    latitude,
                    longitude,
                    station_page_url,
                    measures_url
                FROM air.region_air_station
                WHERE region_ars = :ars
                ORDER BY indicator_key
                """
            ),
            {"ars": ars},
        ).all()
        return [
            (
                str(row[0]),
                str(row[1]),
                str(row[2]) if row[2] is not None else None,
                str(row[3]),
                float(row[4]) if row[4] is not None else None,
                float(row[5]) if row[5] is not None else None,
                str(row[6]) if row[6] is not None else None,
                str(row[7]),
            )
            for row in rows
        ]

    def list_climate_stations(
        self, ars: str
    ) -> list[tuple[str, str, str, float | None, float | None, str | None]]:
        table_exists = self.session.execute(
            text("SELECT to_regclass('climate.region_climate_station') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return []
        rows = self.session.execute(
            text(
                """
                SELECT
                    indicator_key,
                    station_id,
                    station_name,
                    latitude,
                    longitude,
                    source_url
                FROM climate.region_climate_station
                WHERE region_ars = :ars
                ORDER BY indicator_key
                """
            ),
            {"ars": ars},
        ).all()
        return [
            (
                str(row[0]),
                str(row[1]),
                str(row[2]),
                float(row[3]) if row[3] is not None else None,
                float(row[4]) if row[4] is not None else None,
                str(row[5]) if row[5] is not None else None,
            )
            for row in rows
        ]

    def get_land_use_stat(
        self, ars: str
    ) -> tuple[int, float | None, float | None, float | None, float | None, float | None] | None:
        table_exists = self.session.execute(
            text("SELECT to_regclass('landuse.region_area_stat') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return None
        row = self.session.execute(
            text(
                """
                SELECT
                    year,
                    forest_share_pct,
                    settlement_transport_share_pct,
                    agriculture_share_pct,
                    transport_share_pct,
                    settlement_transport_sqm_per_capita
                FROM landuse.region_area_stat
                WHERE region_ars = :ars
                LIMIT 1
                """
            ),
            {"ars": ars},
        ).first()
        if row is None:
            return None
        return (
            int(row[0]),
            float(row[1]) if row[1] is not None else None,
            float(row[2]) if row[2] is not None else None,
            float(row[3]) if row[3] is not None else None,
            float(row[4]) if row[4] is not None else None,
            float(row[5]) if row[5] is not None else None,
        )

    def get_accident_pois_geojson(self, ars: str, category: str) -> dict[str, Any]:
        table_exists = self.session.execute(
            text("SELECT to_regclass('traffic.accident_point') IS NOT NULL")
        ).scalar()
        if not table_exists:
            return {"type": "FeatureCollection", "features": []}

        rows = self.session.execute(
            text(
                """
                SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::json,
                                'properties', json_build_object(
                                    'accident_id', accident_id,
                                    'category', CAST(:category AS text),
                                    'year', year
                                )
                            )
                        ),
                        '[]'::json
                    )
                )
                FROM traffic.accident_point
                WHERE region_ars = :ars
                  AND category = :category
                """
            ),
            {"ars": ars, "category": category},
        ).scalar()
        if rows is None:
            return {"type": "FeatureCollection", "features": []}
        if isinstance(rows, str):
            return json.loads(rows)
        return dict(rows)

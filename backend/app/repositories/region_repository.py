import json
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.ars import lookup_candidates, slugify_region_name
from app.core.config import settings
from app.models.indicator import IndicatorDefinition
from app.models.region import Region
from app.models.score import RegionScoreSnapshot

MANDATORY_SOURCE_LINKS = [
    "https://www.opendata-oepnv.de/ht/de/datensaetze",
    "https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:ags",
]

AMENITY_CATEGORY_MAPPING = {
    "pharmacy": ("amenity", "pharmacy"),
    "doctors": ("amenity", "doctors"),
    "childcare": ("amenity", "kindergarten"),
    "school": ("amenity", "school"),
    "supermarket": ("shop", "supermarket"),
    "station": ("railway", "station"),
    "transit_stop": ("highway", "bus_stop"),
    "playground": ("leisure", "playground"),
    "park": ("leisure", "park"),
}

ACCIDENT_CATEGORY_ORDER = [
    "killed",
    "seriously_injured",
    "slightly_injured",
]

ACCIDENT_CATEGORY_LABELS = {
    "killed": "Getoetete",
    "seriously_injured": "Schwerverletzte",
    "slightly_injured": "Leichtverletzte",
}


class RegionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_regions(self) -> list[Region]:
        statement = select(Region).order_by(Region.name)
        return list(self.session.exec(statement))

    def get_by_ars(self, ars: str) -> Region | None:
        statement = select(Region).where(Region.ars.in_(lookup_candidates(ars)))
        region = self.session.exec(statement).first()
        if region:
            return region

        requested_slug = slugify_region_name(ars)
        slug_statement = select(Region).where(Region.slug == requested_slug).order_by(Region.id)
        return self.session.exec(slug_statement).first()

    def get_score_snapshot(self, region_id: int) -> RegionScoreSnapshot | None:
        statement = (
            select(RegionScoreSnapshot)
            .where(RegionScoreSnapshot.region_id == region_id)
            .where(RegionScoreSnapshot.profile_key == "base")
            .where(RegionScoreSnapshot.period == settings.default_score_period)
        )
        return self.session.exec(statement).first()

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

    def list_source_links(self) -> list[str]:
        statement = (
            select(IndicatorDefinition.source_url)
            .where(IndicatorDefinition.source_url.is_not(None))
            .where(IndicatorDefinition.source_url != "")
            .distinct()
            .order_by(IndicatorDefinition.source_url)
        )
        links = [row for row in self.session.exec(statement)]
        for required in MANDATORY_SOURCE_LINKS:
            if required not in links:
                links.append(required)
        return sorted(set(links))

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

    def get_amenity_pois_geojson(self, ars: str, category: str) -> dict[str, Any] | None:
        mapping = AMENITY_CATEGORY_MAPPING.get(category)
        if mapping is None:
            return None

        boundary_exists = self.session.execute(
            text("SELECT to_regclass('geo.municipality_boundary') IS NOT NULL")
        ).scalar()
        point_exists = self.session.execute(text("SELECT to_regclass('osm.planet_osm_point') IS NOT NULL")).scalar()
        polygon_exists = self.session.execute(text("SELECT to_regclass('osm.planet_osm_polygon') IS NOT NULL")).scalar()
        if not boundary_exists or not point_exists or not polygon_exists:
            return {
                "type": "FeatureCollection",
                "features": [],
            }

        osm_key, osm_value = mapping
        rows = self.session.execute(
            text(
                f"""
                WITH boundary AS (
                    SELECT ST_Transform(geom, 3857) AS geom
                    FROM geo.municipality_boundary
                    WHERE ags = :ars
                    LIMIT 1
                ),
                pois AS (
                    SELECT
                        'point' AS source_type,
                        point.osm_id,
                        COALESCE(point.name, point.tags -> 'name') AS name,
                        ST_AsGeoJSON(ST_Transform(point.way, 4326))::json AS geometry
                    FROM osm.planet_osm_point point
                    CROSS JOIN boundary b
                    WHERE point.way && b.geom
                      AND ST_Covers(b.geom, point.way)
                      AND COALESCE(point."{osm_key}", point.tags -> CAST(:osm_key AS text)) = CAST(:osm_value AS text)

                    UNION ALL

                    SELECT
                        'polygon' AS source_type,
                        polygon.osm_id,
                        COALESCE(polygon.name, polygon.tags -> 'name') AS name,
                        ST_AsGeoJSON(ST_Transform(ST_PointOnSurface(polygon.way), 4326))::json AS geometry
                    FROM osm.planet_osm_polygon polygon
                    CROSS JOIN boundary b
                    WHERE polygon.way && b.geom
                      AND ST_Covers(b.geom, ST_PointOnSurface(polygon.way))
                      AND COALESCE(polygon."{osm_key}", polygon.tags -> CAST(:osm_key AS text)) = CAST(:osm_value AS text)
                )
                SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(
                        json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', geometry,
                                'properties', json_build_object(
                                    'osm_id', osm_id,
                                    'name', name,
                                    'category', CAST(:category AS text),
                                    'source_type', source_type
                                )
                            )
                        ),
                        '[]'::json
                    )
                )
                FROM pois
                """
            ),
            {"ars": ars, "osm_key": osm_key, "osm_value": osm_value, "category": category},
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
        table_exists = self.session.execute(text("SELECT to_regclass('traffic.accident_point') IS NOT NULL")).scalar()
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
        return [(category, counts[category]) for category in ACCIDENT_CATEGORY_ORDER if category in counts]

    def get_accident_pois_geojson(self, ars: str, category: str) -> dict[str, Any]:
        table_exists = self.session.execute(text("SELECT to_regclass('traffic.accident_point') IS NOT NULL")).scalar()
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
                  AND category = CAST(:category AS text)
                """
            ),
            {"ars": ars, "category": category},
        ).scalar()
        if rows is None:
            return {"type": "FeatureCollection", "features": []}
        if isinstance(rows, str):
            return json.loads(rows)
        return dict(rows)

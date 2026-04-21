import logging

from sqlalchemy import text

from app.core.db import engine
from app.etl.common import tracked_etl_run

logger = logging.getLogger("etl.import_postal_codes")
logging.basicConfig(level=logging.INFO)


def _source_tables_ready() -> bool:
    with engine.begin() as connection:
        polygon_exists = connection.execute(
            text("SELECT to_regclass('osm.planet_osm_polygon') IS NOT NULL")
        ).scalar()
        boundary_exists = connection.execute(
            text("SELECT to_regclass('geo.municipality_boundary') IS NOT NULL")
        ).scalar()
        region_exists = connection.execute(text("SELECT to_regclass('region') IS NOT NULL")).scalar()
        postal_area_stage_exists = connection.execute(
            text("SELECT to_regclass('postal.postal_area_stage') IS NOT NULL")
        ).scalar()
        postal_region_exists = connection.execute(
            text("SELECT to_regclass('postal.region_postal_code') IS NOT NULL")
        ).scalar()
    return bool(polygon_exists and boundary_exists and region_exists and postal_area_stage_exists and postal_region_exists)


def rebuild_postal_area_stage() -> int:
    with engine.begin() as connection:
        logger.info("Bereinige entfernte OSM-Postleitzahlflaechen aus postal.postal_area_stage")
        connection.execute(
            text(
                """
                DELETE FROM postal.postal_area_stage stage
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM osm.planet_osm_polygon p
                    WHERE 'planet_osm_polygon:' || p.osm_id::text = stage.source_id
                      AND p.way IS NOT NULL
                      AND COALESCE(p."boundary", p.tags -> 'boundary') = 'postal_code'
                      AND SUBSTRING(
                            regexp_replace(
                                COALESCE(p.tags -> 'postal_code', p.tags -> 'addr:postcode', ''),
                                '[^0-9]',
                                '',
                                'g'
                            )
                            FROM 1 FOR 5
                        ) ~ '^[0-9]{5}$'
                )
                """
            )
        )
        logger.info("Aktualisiere geaenderte OSM-Postleitzahlflaechen in postal.postal_area_stage")
        result = connection.execute(
            text(
                """
                WITH source_rows AS (
                    SELECT
                        'planet_osm_polygon:' || p.osm_id::text AS source_id,
                        SUBSTRING(
                            regexp_replace(
                                COALESCE(p.tags -> 'postal_code', p.tags -> 'addr:postcode', ''),
                                '[^0-9]',
                                '',
                                'g'
                            )
                            FROM 1 FOR 5
                        ) AS postal_code,
                        COALESCE(NULLIF(p."name", ''), p.tags -> 'name') AS postal_name,
                        p.way AS geom_raw
                    FROM osm.planet_osm_polygon p
                    WHERE p.way IS NOT NULL
                      AND COALESCE(p."boundary", p.tags -> 'boundary') = 'postal_code'
                      AND SUBSTRING(
                            regexp_replace(
                                COALESCE(p.tags -> 'postal_code', p.tags -> 'addr:postcode', ''),
                                '[^0-9]',
                                '',
                                'g'
                            )
                            FROM 1 FOR 5
                        ) ~ '^[0-9]{5}$'
                ),
                deduped_source_rows AS (
                    SELECT DISTINCT ON (source_id)
                        source_id,
                        postal_code,
                        postal_name,
                        geom_raw
                    FROM source_rows
                    ORDER BY source_id, postal_code, postal_name
                ),
                changed_rows AS (
                    SELECT
                        src.source_id,
                        src.postal_code,
                        src.postal_name,
                        src.geom_raw
                    FROM deduped_source_rows src
                    LEFT JOIN postal.postal_area_stage stage
                      ON stage.source_id = src.source_id
                    WHERE stage.source_id IS NULL
                       OR stage.postal_code IS DISTINCT FROM src.postal_code
                       OR stage.postal_name IS DISTINCT FROM src.postal_name
                       OR stage.geom_raw IS DISTINCT FROM src.geom_raw
                )
                INSERT INTO postal.postal_area_stage (
                    source_id,
                    postal_code,
                    postal_name,
                    geom_raw,
                    geom,
                    updated_at
                )
                SELECT
                    source_id,
                    postal_code,
                    postal_name,
                    geom_raw,
                    ST_Multi(ST_CollectionExtract(ST_MakeValid(geom_raw), 3)) AS geom,
                    now()
                FROM changed_rows
                ON CONFLICT (source_id) DO UPDATE
                SET postal_code = EXCLUDED.postal_code,
                    postal_name = EXCLUDED.postal_name,
                    geom_raw = EXCLUDED.geom_raw,
                    geom = EXCLUDED.geom,
                    updated_at = EXCLUDED.updated_at
                """
            )
        )
    return int(result.rowcount or 0)


def rebuild_region_postal_codes() -> int:
    if not _source_tables_ready():
        logger.warning(
            "OSM-Polygonquelle, Gemeindegrenzen, Regionstabelle oder Postleitzahl-Stage fehlen. Kein PLZ-Mapping aufgebaut."
        )
        return 0

    with engine.begin() as connection:
        logger.info("Leere vorhandenes PLZ-Mapping postal.region_postal_code")
        connection.execute(text("TRUNCATE postal.region_postal_code"))
        logger.info("Mappe OSM-Postleitzahlgebiete auf Gemeinden")
        result = connection.execute(
            text(
                """
                WITH municipality AS (
                    SELECT
                        b.ags,
                        r.name AS region_name,
                        COALESCE(r.population, 0) AS population,
                        ST_Transform(b.geom, 3857) AS geom
                    FROM geo.municipality_boundary b
                    JOIN region r ON r.ars = b.ags
                    WHERE b.geom IS NOT NULL
                ),
                intersections AS (
                    SELECT
                        pa.postal_code,
                        m.ags AS region_ars,
                        m.region_name,
                        m.population,
                        pa.postal_name,
                        ST_Area(ST_Intersection(pa.geom, m.geom)) AS overlap_area
                    FROM postal.postal_area_stage pa
                    JOIN municipality m
                      ON pa.geom_raw && m.geom
                     AND ST_Intersects(pa.geom_raw, m.geom)
                    WHERE pa.geom IS NOT NULL
                ),
                ranked_candidates AS (
                    SELECT
                        postal_code,
                        region_ars,
                        region_name,
                        population,
                        MAX(postal_name) AS postal_name,
                        MAX(overlap_area) AS overlap_area,
                        ROW_NUMBER() OVER (
                            PARTITION BY postal_code
                            ORDER BY MAX(overlap_area) DESC, population DESC, region_name
                        ) AS postal_rank
                    FROM intersections
                    WHERE overlap_area > 0
                    GROUP BY postal_code, region_ars, region_name, population
                )
                INSERT INTO postal.region_postal_code (
                    postal_code,
                    region_ars,
                    region_name,
                    postal_name,
                    overlap_area,
                    is_primary,
                    updated_at
                )
                SELECT
                    postal_code,
                    region_ars,
                    region_name,
                    postal_name,
                    overlap_area,
                    postal_rank = 1 AS is_primary,
                    now()
                FROM ranked_candidates
                """
            )
        )
    return int(result.rowcount or 0)


def main() -> None:
    logger.info("PLZ-Import gestartet")
    with tracked_etl_run(
        job_name="import_postal_codes",
        sources=[
            {"source_name": "OpenStreetMap postal polygons", "source_url": "osm.planet_osm_polygon"},
            {"source_name": "BKG municipality boundaries", "source_url": "geo.municipality_boundary"},
        ],
    ) as run:
        staged = rebuild_postal_area_stage()
        logger.info("PLZ-Stage geschrieben: %s OSM-Postleitzahlflaechen", staged)
        inserted = rebuild_region_postal_codes()
        run.set_rows_written(inserted)
        logger.info("PLZ-Mapping geschrieben: %s Gemeinde/PLZ-Zuordnungen", inserted)


if __name__ == "__main__":
    main()

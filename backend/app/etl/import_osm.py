import logging
import os
import subprocess
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.etl.common import (
    clear_indicator_values,
    download_file,
    get_or_create_indicator,
    normalize,
    upsert_region_indicator_value,
    with_session,
)

logger = logging.getLogger("etl.import_osm")
logging.basicConfig(level=logging.INFO)

CATEGORY_MAPPING = {
    "pharmacy": [("amenity", "pharmacy")],
    "doctors": [("amenity", "doctors")],
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

OSM_TAG_COLUMNS = sorted(
    {
        osm_key
        for mappings in CATEGORY_MAPPING.values()
        for osm_key, _ in mappings
    }
)


def _build_tag_match_condition(alias: str, mappings: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    clauses: list[str] = []
    params: dict[str, str] = {}
    for index, (osm_key, osm_value) in enumerate(mappings):
        key_param = f"osm_key_{index}"
        value_param = f"osm_value_{index}"
        clauses.append(
            f'COALESCE({alias}."{osm_key}", {alias}.tags -> :{key_param}) = :{value_param}'
        )
        params[key_param] = osm_key
        params[value_param] = osm_value
    return "(" + " OR ".join(clauses) + ")", params


def ensure_osm_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS osm"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS osm.region_amenity_agg (
                    ars varchar(12) NOT NULL,
                    category varchar NOT NULL,
                    count_total integer NOT NULL,
                    per_10k numeric(12, 2) NOT NULL,
                    updated_at timestamp without time zone NOT NULL,
                    PRIMARY KEY (ars, category)
                );
                """
            )
        )


def ensure_osm_indexes() -> None:
    index_statements = [
        (
            "osm_planet_osm_point_way_gix",
            "CREATE INDEX IF NOT EXISTS planet_osm_point_way_gix ON osm.planet_osm_point USING gist (way)",
        ),
        (
            "osm_planet_osm_polygon_way_gix",
            "CREATE INDEX IF NOT EXISTS planet_osm_polygon_way_gix ON osm.planet_osm_polygon USING gist (way)",
        ),
    ]
    for table_name in ("planet_osm_point", "planet_osm_polygon"):
        for column_name in OSM_TAG_COLUMNS:
            index_name = f"osm_{table_name}_{column_name}_idx"
            index_statements.append(
                (
                    index_name,
                    f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON osm.{table_name} ("{column_name}")
                    WHERE "{column_name}" IS NOT NULL
                    """,
                )
            )

    for index_name, sql in index_statements:
        logger.info("Pruefe OSM-Index %s", index_name)
        with engine.begin() as connection:
            connection.execute(text(sql))


def _source_tables_ready() -> bool:
    with engine.begin() as connection:
        planet_point_exists = connection.execute(
            text("SELECT to_regclass('osm.planet_osm_point') IS NOT NULL")
        ).scalar()
        planet_polygon_exists = connection.execute(
            text("SELECT to_regclass('osm.planet_osm_polygon') IS NOT NULL")
        ).scalar()
        boundary_exists = connection.execute(
            text("SELECT to_regclass('geo.municipality_boundary') IS NOT NULL")
        ).scalar()
    return bool(planet_point_exists and planet_polygon_exists and boundary_exists)


def build_real_amenity_aggregation() -> bool:
    ensure_osm_tables()
    if not _source_tables_ready():
        logger.warning(
            "OSM-Quelltabellen oder BKG-Gemeindegrenzen fehlen. Keine synthetischen OSM-Werte werden erzeugt."
        )
        return False

    ensure_osm_indexes()

    with engine.begin() as connection:
        logger.info("Leere alte OSM-Aggregation osm.region_amenity_agg")
        connection.execute(text("TRUNCATE osm.region_amenity_agg"))
        for category, mappings in CATEGORY_MAPPING.items():
            point_condition, point_params = _build_tag_match_condition("point", mappings)
            polygon_condition, polygon_params = _build_tag_match_condition("polygon", mappings)
            logger.info(
                "Aggregiere OSM-Kategorie %s (%s Mapping(s))",
                category,
                len(mappings),
            )
            connection.execute(
                text(
                    f"""
                    WITH boundaries AS (
                        SELECT
                            b.ags,
                            r.population,
                            ST_Transform(b.geom, 3857) AS geom
                        FROM geo.municipality_boundary b
                        JOIN region r ON r.ars = b.ags
                    )
                    INSERT INTO osm.region_amenity_agg (ars, category, count_total, per_10k, updated_at)
                    SELECT
                        b.ags AS ars,
                        :category AS category,
                        COUNT(DISTINCT p.poi_id)::int AS count_total,
                        ROUND(
                            (
                                COUNT(DISTINCT p.poi_id)::numeric
                                / GREATEST(COALESCE(NULLIF(b.population, 0), 10000), 10000)
                            ) * 10000,
                            2
                        ) AS per_10k,
                        now()
                    FROM boundaries b
                    JOIN LATERAL (
                        SELECT 'point:' || point.osm_id::text AS poi_id
                        FROM osm.planet_osm_point point
                        WHERE point.way && b.geom
                          AND ST_Covers(b.geom, point.way)
                          AND {point_condition}

                        UNION ALL

                        SELECT 'polygon:' || polygon.osm_id::text AS poi_id
                        FROM osm.planet_osm_polygon polygon
                        WHERE polygon.way && b.geom
                          AND ST_Covers(b.geom, ST_PointOnSurface(polygon.way))
                          AND {polygon_condition}
                    ) p ON TRUE
                    GROUP BY b.ags, b.population
                    ON CONFLICT (ars, category) DO UPDATE
                    SET count_total = EXCLUDED.count_total,
                        per_10k = EXCLUDED.per_10k,
                        updated_at = now();
                    """
                ),
                {"category": category, **point_params, **polygon_params},
            )
            category_rows = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM osm.region_amenity_agg
                    WHERE category = :category
                    """
                ),
                {"category": category},
            ).scalar() or 0
            logger.info(
                "OSM-Kategorie %s abgeschlossen: %s Gemeinden mit Treffern",
                category,
                category_rows,
            )
        rows_written = connection.execute(text("SELECT COUNT(*) FROM osm.region_amenity_agg")).scalar() or 0
    logger.info("OSM POI-Aggregation geschrieben: %s Gemeinde/Kategorie-Zeilen", rows_written)
    return int(rows_written) > 0


def maybe_download_geofabrik() -> Path | None:
    target = settings.raw_data_path / "osm" / "germany-latest.osm.pbf"
    if target.exists():
        return target
    try:
        return download_file(settings.geofabrik_germany_pbf_url, target, timeout=120)
    except Exception as exc:
        logger.warning("Geofabrik Download fehlgeschlagen: %s", exc)
        return None


def maybe_run_osm2pgsql(osm_path: Path | None) -> None:
    if osm_path is None:
        return

    # osm2pgsql with --hstore requires DB extension hstore. PostGIS is needed for geometry types.
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS hstore"))
        existing_import = connection.execute(
            text(
                """
                SELECT to_regclass('osm.planet_osm_point') IS NOT NULL
                   AND to_regclass('osm.planet_osm_polygon') IS NOT NULL
                """
            )
        ).scalar()
    if existing_import and os.environ.get("OSM_FORCE_IMPORT", "").lower() not in {"1", "true", "yes"}:
        logger.info(
            "OSM-Rohimport uebersprungen: osm.planet_osm_point und osm.planet_osm_polygon existieren bereits. "
            "Setze OSM_FORCE_IMPORT=1 fuer einen Neuimport."
        )
        return

    db_url = make_url(settings.database_url)
    database = db_url.database or "wohnortkompass"
    user = db_url.username or "wohnortkompass"
    host = db_url.host or "localhost"
    port = str(db_url.port or 5432)

    command = [
        "osm2pgsql",
        "--create",
        "--slim",
        "--database",
        database,
        "--user",
        user,
        "--host",
        host,
        "--port",
        port,
        "--schema",
        "osm",
        "--hstore",
        str(osm_path),
    ]
    env = os.environ.copy()
    if db_url.password:
        env["PGPASSWORD"] = db_url.password
    else:
        logger.warning(
            "Kein DB-Passwort in DATABASE_URL gefunden. Falls noetig, PGPASSWORD setzen."
        )
    try:
        subprocess.run(command, check=True, env=env)
        logger.info("osm2pgsql Import erfolgreich")
    except FileNotFoundError:
        logger.warning("osm2pgsql nicht installiert, Import uebersprungen")
    except subprocess.CalledProcessError as exc:
        logger.warning("osm2pgsql Import fehlgeschlagen: %s", exc)


def build_amenities_indicator() -> None:
    with with_session() as session:
        if not build_real_amenity_aggregation():
            return
        indicator = get_or_create_indicator(
            session,
            key="amenities_density",
            name="Alltagsnaehe (OSM POI Dichte)",
            category="amenities",
            unit="per_10k",
            direction="higher_is_better",
            source_name="OpenStreetMap (Geofabrik Extract)",
            source_url="https://download.geofabrik.de/europe/germany.html",
            methodology="Echte Aggregation der OSM POI-Kategorien pro Gemeinde ueber BKG-Gemeindegeometrien, normiert je 10k Einwohner.",
        )
        clear_indicator_values(
            session,
            indicator_id=indicator.id,
            period=settings.default_score_period,
        )

        rows = session.exec(
            text(
                """
                SELECT
                    r.id AS region_id,
                    AVG(a.per_10k)::float AS amenities_raw,
                    COUNT(*)::int AS category_count
                FROM region r
                JOIN osm.region_amenity_agg a
                  ON a.ars = r.ars
                GROUP BY r.id
                """
            )
        ).all()
        if not rows:
            logger.warning("Keine OSM-Aggregation gefunden, amenities wird nicht geschrieben.")
            return

        raw_values = [float(row.amenities_raw) for row in rows]
        normalized = normalize(raw_values, indicator.direction)
        for row, norm in zip(rows, normalized):
            quality_flag = "ok" if int(row.category_count) >= 5 else "low_coverage"
            upsert_region_indicator_value(
                session,
                region_id=int(row.region_id),
                indicator_id=indicator.id,
                period=settings.default_score_period,
                raw_value=float(row.amenities_raw),
                normalized_value=norm,
                quality_flag=quality_flag,
            )


def main() -> None:
    logger.info("OSM-Import gestartet")
    osm_path = maybe_download_geofabrik()
    maybe_run_osm2pgsql(osm_path)
    build_amenities_indicator()
    logger.info("OSM-Import abgeschlossen")


if __name__ == "__main__":
    main()

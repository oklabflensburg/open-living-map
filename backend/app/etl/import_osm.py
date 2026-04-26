import logging
import os
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.db import engine
from app.core.logging import configure_logging
from app.etl.common import (
    clear_indicator_values,
    download_file,
    get_or_create_indicator,
    normalize,
    tracked_etl_run,
    upsert_region_indicator_value,
    with_session,
)

configure_logging()
logger = logging.getLogger("etl.import_osm")

CATEGORY_MAPPING = {
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

CATEGORY_WEIGHTS = {
    "pharmacy": 1.8,
    "doctors": 1.8,
    "hospital": 1.8,
    "childcare": 1.7,
    "school": 1.7,
    "supermarket": 1.8,
    "station": 1.0,
    "transit_stop": 1.6,
    "playground": 0.9,
    "park": 0.5,
    "museum": 0.3,
    "theatre": 0.3,
    "sports_facility": 0.7,
    "theme_park": 0.2,
    "nature_reserve": 0.3,
    "airfield": 0.2,
    "restaurant": 0.7,
    "library": 0.8,
}

TOTAL_CATEGORY_WEIGHT = sum(CATEGORY_WEIGHTS.values())

OSM_TAG_COLUMNS = sorted(
    {osm_key for mappings in CATEGORY_MAPPING.values() for osm_key, _ in mappings}
)


def _build_category_weight_sql(column: str = "a.category") -> str:
    clauses = [f"WHEN '{category}' THEN {weight}" for category, weight in CATEGORY_WEIGHTS.items()]
    return f"CASE {column} " + " ".join(clauses) + " ELSE 1.0 END"


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
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS osm.boundary_3857_stage (
                    ags varchar(12) PRIMARY KEY,
                    population integer NULL,
                    geom geometry(MultiPolygon, 3857) NOT NULL
                );
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS osm.amenity_poi_stage (
                    category varchar NOT NULL,
                    poi_id varchar NOT NULL,
                    name varchar NULL,
                    geom geometry(Point, 3857) NOT NULL,
                    PRIMARY KEY (category, poi_id)
                );
                """
            )
        )
        has_name_column = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'osm'
                      AND table_name = 'amenity_poi_stage'
                      AND column_name = 'name'
                )
                """
            )
        ).scalar()
        if not has_name_column:
            raise RuntimeError(
                "Schema drift detected for osm.amenity_poi_stage: missing column 'name'. "
                "Run `alembic upgrade head` before executing the OSM import."
            )


def ensure_osm_indexes() -> None:
    index_statements = [
        (
            "geo_municipality_boundary_geom_gix",
            "CREATE INDEX IF NOT EXISTS municipality_boundary_geom_idx ON geo.municipality_boundary USING gist (geom)",
        ),
        (
            "osm_planet_osm_point_way_gix",
            "CREATE INDEX IF NOT EXISTS planet_osm_point_way_gix ON osm.planet_osm_point USING gist (way)",
        ),
        (
            "osm_planet_osm_polygon_way_gix",
            "CREATE INDEX IF NOT EXISTS planet_osm_polygon_way_gix ON osm.planet_osm_polygon USING gist (way)",
        ),
        (
            "osm_boundary_3857_stage_geom_gix",
            "CREATE INDEX IF NOT EXISTS boundary_3857_stage_geom_gix ON osm.boundary_3857_stage USING gist (geom)",
        ),
        (
            "osm_amenity_poi_stage_geom_gix",
            "CREATE INDEX IF NOT EXISTS amenity_poi_stage_geom_gix ON osm.amenity_poi_stage USING gist (geom)",
        ),
        (
            "osm_amenity_poi_stage_category_idx",
            "CREATE INDEX IF NOT EXISTS amenity_poi_stage_category_idx ON osm.amenity_poi_stage (category)",
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


def _build_stage_scan_queries(
    table_name: str, alias: str, geom_sql: str
) -> tuple[list[str], dict[str, str]]:
    grouped_by_key: dict[str, dict[str, set[str]]] = {}
    for category, mappings in CATEGORY_MAPPING.items():
        for osm_key, osm_value in mappings:
            grouped_by_key.setdefault(osm_key, {}).setdefault(category, set()).add(osm_value)

    queries: list[str] = []
    params: dict[str, str] = {}

    for osm_key, category_values in grouped_by_key.items():
        all_values = sorted({value for values in category_values.values() for value in values})
        prefilter_placeholders: list[str] = []
        for index, value in enumerate(all_values):
            param_name = f"{table_name}_{osm_key}_prefilter_{index}"
            prefilter_placeholders.append(f":{param_name}")
            params[param_name] = value

        lateral_rows: list[str] = []
        for category, values in category_values.items():
            value_placeholders: list[str] = []
            for index, value in enumerate(sorted(values)):
                param_name = f"{table_name}_{osm_key}_{category}_{index}"
                value_placeholders.append(f":{param_name}")
                params[param_name] = value
            lateral_rows.append(
                f"('{category}', {alias}.\"{osm_key}\" IN ({', '.join(value_placeholders)}))"
            )

        queries.append(
            f"""
            SELECT DISTINCT
                matched.category AS category,
                '{table_name}:' || {alias}.osm_id::text AS poi_id,
                COALESCE(NULLIF({alias}."name", ''), {alias}.tags -> 'name') AS name,
                {geom_sql} AS geom
            FROM osm.{table_name} {alias}
            CROSS JOIN LATERAL (
                VALUES
                    {", ".join(lateral_rows)}
            ) AS matched(category, is_match)
            WHERE {alias}.way IS NOT NULL
              AND {alias}."{osm_key}" IN ({", ".join(prefilter_placeholders)})
              AND matched.is_match
            """
        )

    return queries, params


def rebuild_osm_stage_tables() -> None:
    point_scan_queries, point_params = _build_stage_scan_queries(
        table_name="planet_osm_point",
        alias="point",
        geom_sql="point.way",
    )
    polygon_scan_queries, polygon_params = _build_stage_scan_queries(
        table_name="planet_osm_polygon",
        alias="polygon",
        geom_sql="ST_PointOnSurface(polygon.way)",
    )
    with engine.begin() as connection:
        logger.info("Leere OSM-Stagingtabellen")
        connection.execute(text("TRUNCATE osm.boundary_3857_stage, osm.amenity_poi_stage"))

        logger.info("Materialisiere Gemeindegrenzen in EPSG:3857")
        connection.execute(
            text(
                """
                INSERT INTO osm.boundary_3857_stage (ags, population, geom)
                SELECT
                    b.ags,
                    r.population,
                    ST_Transform(b.geom, 3857) AS geom
                FROM geo.municipality_boundary b
                JOIN region r ON r.ars = b.ags
                WHERE b.geom IS NOT NULL
                """
            )
        )

        logger.info("Materialisiere relevante OSM-POIs für alle Kategorien")
        connection.execute(
            text(
                f"""
                INSERT INTO osm.amenity_poi_stage (category, poi_id, name, geom)
                SELECT DISTINCT ON (category, poi_id)
                    category,
                    poi_id,
                    name,
                    geom
                FROM (
                    {" UNION ALL ".join(point_scan_queries)}
                ) staged
                WHERE geom IS NOT NULL
                ORDER BY category, poi_id, (name IS NULL), name DESC
                ON CONFLICT (category, poi_id) DO UPDATE
                SET name = EXCLUDED.name,
                    geom = EXCLUDED.geom
                """
            ),
            point_params,
        )
        connection.execute(
            text(
                f"""
                INSERT INTO osm.amenity_poi_stage (category, poi_id, name, geom)
                SELECT DISTINCT ON (category, poi_id)
                    category,
                    poi_id,
                    name,
                    geom
                FROM (
                    {" UNION ALL ".join(polygon_scan_queries)}
                ) staged
                WHERE geom IS NOT NULL
                ORDER BY category, poi_id, (name IS NULL), name DESC
                ON CONFLICT (category, poi_id) DO UPDATE
                SET name = EXCLUDED.name,
                    geom = EXCLUDED.geom
                """
            ),
            polygon_params,
        )


def build_real_amenity_aggregation() -> bool:
    ensure_osm_tables()
    if not _source_tables_ready():
        logger.warning(
            "OSM-Quelltabellen oder BKG-Gemeindegrenzen fehlen. Keine synthetischen OSM-Werte werden erzeugt."
        )
        return False

    ensure_osm_indexes()
    rebuild_osm_stage_tables()

    with engine.begin() as connection:
        logger.info("Leere alte OSM-Aggregation osm.region_amenity_agg")
        connection.execute(text("TRUNCATE osm.region_amenity_agg"))
        logger.info("Aggregiere OSM-Kategorien in einem gemeinsamen räumlichen Durchlauf")
        connection.execute(
            text(
                """
                INSERT INTO osm.region_amenity_agg (ars, category, count_total, per_10k, updated_at)
                SELECT
                    b.ags AS ars,
                    p.category AS category,
                    COUNT(DISTINCT p.poi_id)::int AS count_total,
                    ROUND(
                        (
                            COUNT(DISTINCT p.poi_id)::numeric
                            / GREATEST(COALESCE(NULLIF(b.population, 0), 10000), 10000)
                        ) * 10000,
                        2
                    ) AS per_10k,
                    now()
                FROM osm.boundary_3857_stage b
                JOIN osm.amenity_poi_stage p
                  ON p.geom && b.geom
                 AND ST_Covers(b.geom, p.geom)
                GROUP BY b.ags, b.population, p.category
                ON CONFLICT (ars, category) DO UPDATE
                SET count_total = EXCLUDED.count_total,
                    per_10k = EXCLUDED.per_10k,
                    updated_at = now();
                """
            )
        )
        rows_written = (
            connection.execute(text("SELECT COUNT(*) FROM osm.region_amenity_agg")).scalar() or 0
        )
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
    if existing_import and os.environ.get("OSM_FORCE_IMPORT", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
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
            normalization_mode="log",
            source_name="OpenStreetMap (Geofabrik Extract)",
            source_url="https://download.geofabrik.de/europe/germany.html",
            methodology="Echte Aggregation der OSM-POI-Kategorien pro Gemeinde ueber BKG-Gemeindegeometrien. Der Rohwert ist eine fachlich gewichtete Dichte je 10.000 Einwohner, bei der Grundversorgung wie Apotheken, Aerzte, Krankenhaeuser, Supermaerkte, Kitas, Schulen und Haltestellen deutlich staerker zaehlt als Freizeit- oder Spezialangebote. Der normierte Score kombiniert diese Dichte zu 75 Prozent mit der Breite des Angebots, also der Anzahl abgedeckter OSM-Kategorien, zu 25 Prozent. Die Dichte wird logarithmisch normiert, damit Ausreisser grosser Staedte den Score nicht unverhaeltnismaessig dominieren.",
        )
        clear_indicator_values(
            session,
            indicator_id=indicator.id,
            period=settings.default_score_period,
        )

        rows = session.execute(
            text(
                f"""
                SELECT
                    r.id AS region_id,
                    (SUM(a.per_10k * {_build_category_weight_sql()}) / :total_category_weight)::float AS amenities_raw,
                    COUNT(*)::int AS category_count
                FROM region r
                JOIN osm.region_amenity_agg a
                  ON a.ars = r.ars
                GROUP BY r.id
                """
            ),
            {"total_category_weight": TOTAL_CATEGORY_WEIGHT},
        ).all()
        if not rows:
            logger.warning("Keine OSM-Aggregation gefunden, amenities wird nicht geschrieben.")
            return

        raw_values = [float(row.amenities_raw) for row in rows]
        category_counts = [int(row.category_count) for row in rows]
        density_scores = normalize(raw_values, indicator.direction, mode="log")
        breadth_scores = normalize(
            [float(count) for count in category_counts], indicator.direction, mode="linear"
        )

        for row, density_score, breadth_score in zip(
            rows, density_scores, breadth_scores, strict=True
        ):
            norm = round((density_score * 0.75) + (breadth_score * 0.25), 2)
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
    with tracked_etl_run(
        job_name="import_osm",
        sources=[
            {
                "source_name": "Geofabrik Germany PBF",
                "source_url": settings.geofabrik_germany_pbf_url,
            },
        ],
    ) as run:
        osm_path = maybe_download_geofabrik()
        maybe_run_osm2pgsql(osm_path)
        build_amenities_indicator()
        run.set_rows_written(0)
        logger.info("OSM-Import abgeschlossen")


if __name__ == "__main__":
    main()

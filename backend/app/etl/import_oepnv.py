import logging
import io
import csv
import zipfile
import time
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
import psycopg
from psycopg import sql
from sqlalchemy import bindparam, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.etl.common import (
    clear_indicator_values,
    get_or_create_indicator,
    normalize,
    upsert_region_indicator_value,
    with_session,
)

logger = logging.getLogger("etl.import_oepnv")
logging.basicConfig(level=logging.INFO)

SOURCE_URL = "https://www.opendata-oepnv.de/ht/de/datensaetze"
BIN_SIZE_MINUTES = 15
OEPNV_IMPORT_LOCK_ID = 90421001
LOCKFILE_NAME = "import_oepnv.lock"
_LOCK_FD: int | None = None


def _parse_gtfs_urls() -> list[str]:
    raw = settings.oepnv_gtfs_urls
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _acquire_import_lock() -> bool:
    global _LOCK_FD
    lock_path = settings.staging_data_path / LOCKFILE_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return False
    _LOCK_FD = fd
    return True


def _release_import_lock() -> None:
    global _LOCK_FD
    if _LOCK_FD is None:
        return
    import fcntl

    fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
    os.close(_LOCK_FD)
    _LOCK_FD = None


def _resolve_local_gtfs(entry: str) -> Path | None:
    parsed = urlparse(entry)
    if parsed.scheme in {"http", "https"}:
        return None

    if parsed.scheme == "file":
        candidate = Path(unquote(parsed.path)).expanduser()
    else:
        candidate = Path(entry).expanduser()

    if not candidate.exists():
        raise FileNotFoundError(f"GTFS-Datei nicht gefunden: {candidate}")
    if not zipfile.is_zipfile(candidate):
        raise RuntimeError(f"Datei ist kein GTFS-ZIP: {candidate}")
    logger.info("Nutze lokale GTFS-Datei: %s", candidate)
    return candidate.resolve()


def _download_gtfs(url: str) -> Path:
    local_path = _resolve_local_gtfs(url)
    if local_path is not None:
        return local_path

    parsed = urlparse(url)
    name = Path(parsed.path).name or "gtfs.zip"
    if not name.endswith(".zip"):
        name = f"{name}.zip"
    target = settings.raw_data_path / "oepnv" / name
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and zipfile.is_zipfile(target):
        logger.info("GTFS Download uebersprungen, Datei vorhanden: %s", target)
        return target

    auth = None
    if settings.oepnv_http_username and settings.oepnv_http_password:
        auth = (settings.oepnv_http_username, settings.oepnv_http_password)

    logger.info("Download GTFS: %s", url)
    with httpx.Client(timeout=180, follow_redirects=True, auth=auth) as client:
        response = client.get(url)
        response.raise_for_status()
        target.write_bytes(response.content)

    if not zipfile.is_zipfile(target):
        content_type = response.headers.get("content-type", "")
        final_url = str(response.url)
        target.unlink(missing_ok=True)
        raise RuntimeError(
            f"Download ist kein GTFS-ZIP (content-type={content_type}). "
            f"Wahrscheinlich Redirect/Login-Seite (final_url={final_url}). "
            "Bitte gueltigen Direktlink nutzen oder ZIP manuell laden und als lokalen Pfad in OEPNV_GTFS_URLS setzen."
        )

    logger.info("GTFS geladen: %s", target)
    return target


def _psycopg_conn_string() -> str:
    db_url = make_url(settings.database_url)
    if not db_url.drivername.startswith("postgresql"):
        raise RuntimeError(f"Nicht unterstuetzte DATABASE_URL fuer psycopg: {db_url.drivername}")

    host = db_url.host or "localhost"
    port = db_url.port or 5432
    dbname = db_url.database or "postgres"
    user = db_url.username or "postgres"
    password = db_url.password or ""
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def _open_gtfs_member(zf: zipfile.ZipFile, filename: str):
    for name in zf.namelist():
        if name.lower().endswith(f"/{filename}") or name.lower() == filename.lower():
            return zf.open(name, "r")
    return None


def _gtfs_headers_and_rows(zf: zipfile.ZipFile, filename: str) -> tuple[list[str], io.TextIOWrapper] | None:
    handle = _open_gtfs_member(zf, filename)
    if handle is None:
        return None

    text_handle = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
    reader = csv.reader(text_handle)
    try:
        headers = next(reader)
    except StopIteration:
        text_handle.close()
        return None

    text_handle.seek(0)
    return headers, text_handle


def _create_gtfs_text_table(
    conn: psycopg.Connection,
    *,
    schema_name: str,
    table_name: str,
    headers: list[str],
) -> None:
    sanitized_headers = [header.strip() for header in headers if header.strip()]
    if not sanitized_headers:
        raise RuntimeError(f"GTFS-Datei {table_name} ohne Header")

    columns = sql.SQL(", ").join(
        sql.SQL("{} text").format(sql.Identifier(column_name)) for column_name in sanitized_headers
    )
    query = sql.SQL("CREATE TABLE {}.{} ({})").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
        columns,
    )
    with conn.cursor() as cur:
        cur.execute(query)


def _copy_gtfs_text_table(
    conn: psycopg.Connection,
    *,
    schema_name: str,
    table_name: str,
    text_handle: io.TextIOWrapper,
) -> None:
    copy_sql = sql.SQL("COPY {}.{} FROM STDIN WITH (FORMAT csv, HEADER true)").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )
    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            while chunk := text_handle.read(1024 * 1024):
                copy.write(chunk)


def _import_gtfs_to_postgres(gtfs_zip: Path, schema_name: str) -> None:
    files_to_import = ["stops.txt", "trips.txt", "calendar.txt", "stop_times.txt"]
    import_schema_name = schema_name

    logger.info("Importiere GTFS-Tabellen direkt nach PostgreSQL in Schema %s", schema_name)
    with psycopg.connect(_psycopg_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute("SET lock_timeout = '2s'")
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(import_schema_name)))
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(import_schema_name)))
        conn.commit()

        with zipfile.ZipFile(gtfs_zip, "r") as zf:
            for filename in files_to_import:
                header_and_handle = _gtfs_headers_and_rows(zf, filename)
                if header_and_handle is None:
                    logger.warning("GTFS-Datei fehlt und wird uebersprungen: %s", filename)
                    continue

                headers, text_handle = header_and_handle
                table_name = filename.removesuffix(".txt")
                logger.info("Lade GTFS-Datei %s", filename)
                started_at = time.monotonic()
                try:
                    _create_gtfs_text_table(
                        conn,
                        schema_name=import_schema_name,
                        table_name=table_name,
                        headers=headers,
                    )
                    _copy_gtfs_text_table(
                        conn,
                        schema_name=import_schema_name,
                        table_name=table_name,
                        text_handle=text_handle,
                    )
                    conn.commit()
                    logger.info(
                        "GTFS-Datei %s importiert (%.1fs)",
                        filename,
                        time.monotonic() - started_at,
                    )
                finally:
                    text_handle.close()


def _schema_has_table(schema_name: str, table_name: str) -> bool:
    with with_session() as session:
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema_name AND table_name = :table_name
                LIMIT 1;
                """
            ),
            {"schema_name": schema_name, "table_name": table_name},
        ).first()
    return row is not None


def _schema_has_column(schema_name: str, table_name: str, column_name: str) -> bool:
    with with_session() as session:
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = :schema_name
                  AND table_name = :table_name
                  AND column_name = :column_name
                LIMIT 1;
                """
            ),
            {"schema_name": schema_name, "table_name": table_name, "column_name": column_name},
        ).first()
    return row is not None


def _municipality_boundaries_ready() -> bool:
    with with_session() as session:
        table_exists = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'geo'
                      AND table_name = 'municipality_boundary'
                )
                """
            )
        ).scalar()
        if not table_exists:
            return False

        row_count = session.execute(text("SELECT COUNT(*) FROM geo.municipality_boundary")).scalar() or 0
    return int(row_count) > 0


def _prepare_staging() -> str:
    with with_session() as session:
        session.execute(text("SET lock_timeout = '2s'"))
        session.exec(text("CREATE SCHEMA IF NOT EXISTS oepnv;"))
        session.exec(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        session.exec(
            text(
                """
                CREATE TABLE IF NOT EXISTS oepnv.gtfs_feed_registry (
                    feed_key text PRIMARY KEY,
                    source_path text NOT NULL,
                    schema_name text NOT NULL,
                    file_size bigint NOT NULL,
                    modified_at double precision NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now()
                );
                """
            )
        )
        session.exec(text("ALTER TABLE oepnv.gtfs_feed_registry ADD COLUMN IF NOT EXISTS schema_name text"))
        session.exec(
            text(
                """
                CREATE TABLE IF NOT EXISTS oepnv.gtfs_stage_registry (
                    feed_key text PRIMARY KEY,
                    municipality_signature text NOT NULL,
                    active_stage_key text,
                    updated_at timestamptz NOT NULL DEFAULT now()
                );
                """
            )
        )
        session.exec(text("ALTER TABLE oepnv.gtfs_stage_registry ADD COLUMN IF NOT EXISTS active_stage_key text"))

        session.exec(
            text(
                """
                CREATE TABLE IF NOT EXISTS oepnv.gtfs_stop_region_map (
                    feed_key text NOT NULL,
                    stop_id text NOT NULL,
                    region_id integer NOT NULL,
                    stop_lat double precision NOT NULL,
                    stop_lon double precision NOT NULL,
                    PRIMARY KEY (feed_key, stop_id)
                );
                """
            )
        )
        session.exec(
            text(
                """
                CREATE TABLE IF NOT EXISTS oepnv.gtfs_stop_departures (
                    feed_key text NOT NULL,
                    stop_id text NOT NULL,
                    region_id integer NOT NULL,
                    departures double precision NOT NULL,
                    PRIMARY KEY (feed_key, stop_id)
                );
                """
            )
        )
        session.exec(
            text(
                """
                CREATE TABLE IF NOT EXISTS oepnv.gtfs_stop_bin_departures (
                    feed_key text NOT NULL,
                    stop_id text NOT NULL,
                    region_id integer NOT NULL,
                    bin_idx integer NOT NULL,
                    departures double precision NOT NULL,
                    PRIMARY KEY (feed_key, stop_id, bin_idx)
                );
                """
            )
        )
        session.exec(
            text(
                """
                CREATE TABLE IF NOT EXISTS oepnv.municipality_centroids (
                    municipality_id integer PRIMARY KEY,
                    geom geometry(Point, 4326) NOT NULL
                );
                """
            )
        )
        session.exec(
            text(
                """
                INSERT INTO oepnv.municipality_centroids (municipality_id, geom)
                SELECT
                    id,
                    ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)
                FROM region
                WHERE level = 'gemeinde'
                  AND centroid_lat IS NOT NULL
                  AND centroid_lon IS NOT NULL
                ON CONFLICT (municipality_id) DO UPDATE
                SET geom = EXCLUDED.geom;
                """
            )
        )
        session.execute(
            text(
                """
                DELETE FROM oepnv.municipality_centroids mc
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM region r
                    WHERE r.id = mc.municipality_id
                      AND r.level = 'gemeinde'
                      AND r.centroid_lat IS NOT NULL
                      AND r.centroid_lon IS NOT NULL
                );
                """
            )
        )
        session.exec(
            text(
                """
                CREATE INDEX IF NOT EXISTS municipality_centroids_geom_idx
                ON oepnv.municipality_centroids
                USING gist (geom);
                """
            )
        )
        municipality_signature = session.execute(
            text(
                """
                SELECT md5(
                    COALESCE(
                        string_agg(
                            id::text || ':' ||
                            COALESCE(centroid_lat::text, '') || ':' ||
                            COALESCE(centroid_lon::text, '') || ':' ||
                            COALESCE(population::text, ''),
                            '|' ORDER BY id
                        ),
                        ''
                    )
                )
                FROM region
                WHERE level = 'gemeinde'
                """
            )
        ).scalar() or ""
        session.commit()
    return str(municipality_signature)


def _gtfs_file_signature(gtfs_zip: Path) -> tuple[str, int, float]:
    stat = gtfs_zip.stat()
    return str(gtfs_zip.resolve()), stat.st_size, stat.st_mtime


def _get_feed_registry(feed_key: str) -> tuple[str, str, int, float] | None:
    with with_session() as session:
        row = session.execute(
            text(
                """
                SELECT schema_name, source_path, file_size, modified_at
                FROM oepnv.gtfs_feed_registry
                WHERE feed_key = :feed_key
                """
            ),
            {"feed_key": feed_key},
        ).first()
    if row is None:
        return None
    return str(row[0]), str(row[1]), int(row[2]), float(row[3])


def _should_import_gtfs(feed_key: str, gtfs_zip: Path) -> bool:
    registry_row = _get_feed_registry(feed_key)
    if registry_row is None:
        return True
    schema_name, source_path_db, file_size_db, modified_at_db = registry_row
    if not all(_schema_has_table(schema_name, table_name) for table_name in ["stops", "trips", "stop_times"]):
        return True

    source_path, file_size, modified_at = _gtfs_file_signature(gtfs_zip)
    return not (
        source_path_db == source_path
        and file_size_db == int(file_size)
        and modified_at_db == float(modified_at)
    )


def _store_feed_registry(feed_key: str, gtfs_zip: Path, schema_name: str) -> None:
    source_path, file_size, modified_at = _gtfs_file_signature(gtfs_zip)
    with with_session() as session:
        session.execute(
            text(
                """
                INSERT INTO oepnv.gtfs_feed_registry (feed_key, source_path, schema_name, file_size, modified_at, updated_at)
                VALUES (:feed_key, :source_path, :schema_name, :file_size, :modified_at, now())
                ON CONFLICT (feed_key) DO UPDATE
                SET source_path = EXCLUDED.source_path,
                    schema_name = EXCLUDED.schema_name,
                    file_size = EXCLUDED.file_size,
                    modified_at = EXCLUDED.modified_at,
                    updated_at = now()
                """
            ),
            {
                "feed_key": feed_key,
                "source_path": source_path,
                "schema_name": schema_name,
                "file_size": file_size,
                "modified_at": modified_at,
            },
        )
        session.commit()


def _has_stage_rows(feed_key: str) -> bool:
    with with_session() as session:
        row = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM oepnv.gtfs_stop_region_map
                    WHERE feed_key = :feed_key
                )
                """
            ),
            {"feed_key": feed_key},
        ).scalar()
    return bool(row)


def _get_stage_registry(feed_key: str) -> tuple[str, str | None] | None:
    with with_session() as session:
        row = session.execute(
            text(
                """
                SELECT municipality_signature, active_stage_key
                FROM oepnv.gtfs_stage_registry
                WHERE feed_key = :feed_key
                """
            ),
            {"feed_key": feed_key},
        ).first()
    if row is None:
        return None
    return str(row[0]), (str(row[1]) if row[1] is not None else None)


def _should_rebuild_staging(feed_key: str, municipality_signature: str) -> bool:
    stage_registry = _get_stage_registry(feed_key)
    if stage_registry is None:
        return True
    stored_signature, active_stage_key = stage_registry
    if not active_stage_key:
        return True
    if not _has_stage_rows(active_stage_key):
        return True
    return stored_signature != municipality_signature


def _store_stage_registry(feed_key: str, municipality_signature: str, active_stage_key: str) -> None:
    with with_session() as session:
        session.execute(
            text(
                """
                INSERT INTO oepnv.gtfs_stage_registry (feed_key, municipality_signature, active_stage_key, updated_at)
                VALUES (:feed_key, :municipality_signature, :active_stage_key, now())
                ON CONFLICT (feed_key) DO UPDATE
                SET municipality_signature = EXCLUDED.municipality_signature,
                    active_stage_key = EXCLUDED.active_stage_key,
                    updated_at = now()
                """
            ),
            {
                "feed_key": feed_key,
                "municipality_signature": municipality_signature,
                "active_stage_key": active_stage_key,
            },
        )
        session.commit()


def _create_feed_indexes(schema_name: str) -> None:
    with with_session() as session:
        if _schema_has_table(schema_name, "stops"):
            session.exec(
                text(f'CREATE INDEX IF NOT EXISTS {schema_name}_stops_stop_id_idx ON "{schema_name}".stops (stop_id);')
            )
        if _schema_has_table(schema_name, "stop_times"):
            session.exec(
                text(
                    f'CREATE INDEX IF NOT EXISTS {schema_name}_stop_times_stop_id_idx ON "{schema_name}".stop_times (stop_id);'
                )
            )
            session.exec(
                text(
                    f'CREATE INDEX IF NOT EXISTS {schema_name}_stop_times_trip_id_idx ON "{schema_name}".stop_times (trip_id);'
                )
            )
        if _schema_has_table(schema_name, "trips"):
            session.exec(
                text(f'CREATE INDEX IF NOT EXISTS {schema_name}_trips_trip_id_idx ON "{schema_name}".trips (trip_id);')
            )
            session.exec(
                text(
                    f'CREATE INDEX IF NOT EXISTS {schema_name}_trips_service_id_idx ON "{schema_name}".trips (service_id);'
                )
            )
        if _schema_has_table(schema_name, "calendar"):
            session.exec(
                text(
                    f'CREATE INDEX IF NOT EXISTS {schema_name}_calendar_service_id_idx ON "{schema_name}".calendar (service_id);'
                )
            )
        session.commit()


def _load_feed_into_staging(stage_key: str, schema_name: str) -> None:
    if not _schema_has_table(schema_name, "stops"):
        raise RuntimeError(f"GTFS-Schema {schema_name} enthaelt keine stops-Tabelle")
    if not _municipality_boundaries_ready():
        raise RuntimeError(
            "geo.municipality_boundary fehlt oder ist leer. "
            "Bitte zuerst `python -m app.etl.import_bkg` ausfuehren."
        )

    _create_feed_indexes(schema_name)

    location_type_expr = "COALESCE(NULLIF(s.location_type::text, ''), '0')"
    if not _schema_has_column(schema_name, "stops", "location_type"):
        location_type_expr = "'0'"

    with with_session() as session:
        logger.info("Baue GTFS-Stage stop->municipality mapping (%s)", stage_key)
        session.execute(
            text(
                f"""
                INSERT INTO oepnv.gtfs_stop_region_map (feed_key, stop_id, region_id, stop_lat, stop_lon)
                SELECT
                    :stage_key,
                    s.stop_id::text,
                    COALESCE(boundary_match.municipality_id, nearest.municipality_id),
                    s.stop_lat_num,
                    s.stop_lon_num
                FROM (
                    SELECT
                        stop_id,
                        stop_lat::double precision AS stop_lat_num,
                        stop_lon::double precision AS stop_lon_num,
                        ST_SetSRID(ST_MakePoint(stop_lon::double precision, stop_lat::double precision), 4326) AS geom,
                        {location_type_expr} AS location_type
                    FROM {schema_name}.stops s
                    WHERE stop_id IS NOT NULL
                      AND NULLIF(stop_lat::text, '') ~ '^-?\\d+(\\.\\d+)?$'
                      AND NULLIF(stop_lon::text, '') ~ '^-?\\d+(\\.\\d+)?$'
                ) s
                LEFT JOIN LATERAL (
                    SELECT r.id AS municipality_id
                    FROM geo.municipality_boundary b
                    JOIN region r
                      ON r.ars = b.ags
                     AND r.level = 'gemeinde'
                    WHERE ST_Covers(b.geom, s.geom)
                    ORDER BY ST_Area(b.geom) ASC
                    LIMIT 1
                ) boundary_match ON TRUE
                LEFT JOIN LATERAL (
                    SELECT m.municipality_id
                    FROM oepnv.municipality_centroids m
                    ORDER BY m.geom <-> s.geom
                    LIMIT 1
                ) nearest ON TRUE
                WHERE s.location_type IN ('0')
                  AND COALESCE(boundary_match.municipality_id, nearest.municipality_id) IS NOT NULL;
                """
            ),
            {"stage_key": stage_key},
        )

        if not _schema_has_table(schema_name, "stop_times") or not _schema_has_table(schema_name, "trips"):
            session.commit()
            return

        calendar_join = ""
        calendar_weight_expr = "1.0"
        if _schema_has_table(schema_name, "calendar"):
            calendar_join = f"LEFT JOIN {schema_name}.calendar c ON c.service_id::text = t.service_id::text"
            calendar_weight_expr = (
                "GREATEST(("
                "COALESCE(NULLIF(c.monday::text, '')::int, 0) + "
                "COALESCE(NULLIF(c.tuesday::text, '')::int, 0) + "
                "COALESCE(NULLIF(c.wednesday::text, '')::int, 0) + "
                "COALESCE(NULLIF(c.thursday::text, '')::int, 0) + "
                "COALESCE(NULLIF(c.friday::text, '')::int, 0) + "
                "COALESCE(NULLIF(c.saturday::text, '')::int, 0) + "
                "COALESCE(NULLIF(c.sunday::text, '')::int, 0)"
                ") / 7.0, 1.0/7.0)"
            )

        logger.info("Aggregiere GTFS-Abfahrten je Haltestelle (%s)", stage_key)
        session.execute(
            text(
                f"""
                INSERT INTO oepnv.gtfs_stop_departures (feed_key, stop_id, region_id, departures)
                WITH trip_weight AS (
                    SELECT t.trip_id::text AS trip_id, {calendar_weight_expr} AS weight
                    FROM {schema_name}.trips t
                    {calendar_join}
                ),
                valid_stop_times AS (
                    SELECT
                        st.stop_id::text AS stop_id,
                        st.trip_id::text AS trip_id,
                        (
                            (
                                split_part(st.departure_time::text, ':', 1)::int * 60
                                + split_part(st.departure_time::text, ':', 2)::int
                            ) % 1440
                        ) AS dep_minute
                    FROM {schema_name}.stop_times st
                    WHERE st.stop_id IS NOT NULL
                      AND st.trip_id IS NOT NULL
                      AND st.departure_time IS NOT NULL
                      AND st.departure_time::text ~ '^[0-9]{{1,3}}:[0-9]{{2}}(:[0-9]{{2}})?$'
                      AND split_part(st.departure_time::text, ':', 2)::int BETWEEN 0 AND 59
                )
                SELECT
                    :stage_key,
                    m.stop_id,
                    m.region_id,
                    SUM(COALESCE(tw.weight, 1.0)) AS departures
                FROM valid_stop_times vst
                JOIN oepnv.gtfs_stop_region_map m
                  ON m.feed_key = :stage_key
                 AND m.stop_id = vst.stop_id
                LEFT JOIN trip_weight tw
                  ON tw.trip_id = vst.trip_id
                GROUP BY m.stop_id, m.region_id
                ON CONFLICT (feed_key, stop_id) DO UPDATE
                SET departures = EXCLUDED.departures,
                    region_id = EXCLUDED.region_id;
                """
            ),
            {"stage_key": stage_key},
        )

        logger.info("Aggregiere GTFS-Regelmaessigkeit je Zeitfenster (%s)", stage_key)
        session.execute(
            text(
                f"""
                INSERT INTO oepnv.gtfs_stop_bin_departures (feed_key, stop_id, region_id, bin_idx, departures)
                WITH trip_weight AS (
                    SELECT t.trip_id::text AS trip_id, {calendar_weight_expr} AS weight
                    FROM {schema_name}.trips t
                    {calendar_join}
                ),
                valid_stop_times AS (
                    SELECT
                        st.stop_id::text AS stop_id,
                        st.trip_id::text AS trip_id,
                        (
                            (
                                split_part(st.departure_time::text, ':', 1)::int * 60
                                + split_part(st.departure_time::text, ':', 2)::int
                            ) % 1440
                        ) AS dep_minute
                    FROM {schema_name}.stop_times st
                    WHERE st.stop_id IS NOT NULL
                      AND st.trip_id IS NOT NULL
                      AND st.departure_time IS NOT NULL
                      AND st.departure_time::text ~ '^[0-9]{{1,3}}:[0-9]{{2}}(:[0-9]{{2}})?$'
                      AND split_part(st.departure_time::text, ':', 2)::int BETWEEN 0 AND 59
                )
                SELECT
                    :stage_key,
                    m.stop_id,
                    m.region_id,
                    (vst.dep_minute / :bin_size)::int AS bin_idx,
                    SUM(COALESCE(tw.weight, 1.0)) AS departures
                FROM valid_stop_times vst
                JOIN oepnv.gtfs_stop_region_map m
                  ON m.feed_key = :stage_key
                 AND m.stop_id = vst.stop_id
                LEFT JOIN trip_weight tw
                  ON tw.trip_id = vst.trip_id
                GROUP BY m.stop_id, m.region_id, (vst.dep_minute / :bin_size)::int
                ON CONFLICT (feed_key, stop_id, bin_idx) DO UPDATE
                SET departures = EXCLUDED.departures,
                    region_id = EXCLUDED.region_id;
                """
            ),
            {"stage_key": stage_key, "bin_size": BIN_SIZE_MINUTES},
        )
        session.commit()


def _fetch_metric_values(sql: str, params: dict[str, object] | None = None) -> list[tuple[int, float]]:
    with with_session() as session:
        statement = text(sql)
        if params and "active_stage_keys" in params:
            statement = statement.bindparams(bindparam("active_stage_keys", expanding=True))
        rows = session.execute(statement, params or {}).all()
    values: list[tuple[int, float]] = []
    for row in rows:
        region_id = int(row[0])
        metric = float(row[1])
        values.append((region_id, metric))
    return values


def _compute_metrics(active_stage_keys: list[str]) -> tuple[list[tuple[int, float]], list[tuple[int, float]], list[tuple[int, float]]]:
    params = {"active_stage_keys": active_stage_keys}
    stop_density_values = _fetch_metric_values(
        """
        SELECT
            m.region_id,
            (
                COUNT(DISTINCT (ROUND(m.stop_lat::numeric, 6), ROUND(m.stop_lon::numeric, 6)))::double precision
                / GREATEST(COALESCE(r.population, 0), 10000)::double precision
            ) * 10000 AS stops_per_10k
        FROM oepnv.gtfs_stop_region_map m
        JOIN region r ON r.id = m.region_id
        WHERE m.feed_key IN :active_stage_keys
        GROUP BY m.region_id, r.population
        HAVING COUNT(*) > 0;
        """,
        params,
    )

    departures_values = _fetch_metric_values(
        """
        SELECT
            d.region_id,
            (
                SUM(d.departures)
                / GREATEST(COALESCE(r.population, 0), 10000)::double precision
            ) * 10000 AS departures_per_10k
        FROM oepnv.gtfs_stop_departures d
        JOIN region r ON r.id = d.region_id
        WHERE d.feed_key IN :active_stage_keys
        GROUP BY d.region_id, r.population
        HAVING SUM(d.departures) > 0;
        """,
        params,
    )

    regularity_values = _fetch_metric_values(
        """
        WITH stop_non_zero_bins AS (
            SELECT
                feed_key,
                stop_id,
                region_id,
                departures
            FROM oepnv.gtfs_stop_bin_departures
            WHERE departures > 0
              AND feed_key IN :active_stage_keys
        ),
        stop_stats AS (
            SELECT
                feed_key,
                stop_id,
                region_id,
                AVG(departures) AS mean_departures,
                STDDEV_POP(departures) AS std_departures,
                COUNT(*) AS non_zero_bin_count
            FROM stop_non_zero_bins
            GROUP BY feed_key, stop_id, region_id
        ),
        stop_regularity AS (
            SELECT
                s.feed_key,
                s.stop_id,
                s.region_id,
                CASE
                    WHEN s.non_zero_bin_count >= 2 AND s.mean_departures > 0
                    THEN 1.0 / (1.0 + (COALESCE(s.std_departures, 0.0) / s.mean_departures))
                    ELSE NULL
                END AS regularity,
                d.departures AS weight_departures
            FROM stop_stats s
            JOIN oepnv.gtfs_stop_departures d
              ON d.feed_key = s.feed_key
             AND d.stop_id = s.stop_id
             AND d.region_id = s.region_id
        )
        SELECT
            region_id,
            (SUM(regularity * weight_departures) / NULLIF(SUM(weight_departures), 0)) * 100.0 AS regularity_index
        FROM stop_regularity
        WHERE regularity IS NOT NULL AND weight_departures > 0
        GROUP BY region_id;
        """,
        params,
    )

    return stop_density_values, departures_values, regularity_values


def _write_indicator(
    *,
    key: str,
    name: str,
    category: str,
    unit: str,
    direction: str,
    methodology: str,
    normalization_mode: str,
    values: list[tuple[int, float]],
) -> None:
    with with_session() as session:
        indicator = get_or_create_indicator(
            session,
            key=key,
            name=name,
            category=category,
            unit=unit,
            direction=direction,
            normalization_mode=normalization_mode,
            source_name="OpenData OePNV (GTFS)",
            source_url=SOURCE_URL,
            methodology=methodology,
        )
        clear_indicator_values(session, indicator_id=indicator.id, period=settings.default_score_period)

        if not values:
            return

        raw_values = [raw for _, raw in values]
        normalized_values = normalize(raw_values, direction, mode=normalization_mode)
        for (region_id, raw), norm in zip(values, normalized_values):
            quality_flag = "ok" if raw > 0 else "low_coverage"
            upsert_region_indicator_value(
                session,
                region_id=region_id,
                indicator_id=indicator.id,
                period=settings.default_score_period,
                raw_value=round(raw, 6),
                normalized_value=norm,
                quality_flag=quality_flag,
            )


def main() -> None:
    logger.info("OEPNV-Import gestartet")
    if not _acquire_import_lock():
        logger.warning("OEPNV-Import bereits aktiv. Neuer Lauf wird beendet statt auf DB-Locks zu warten.")
        return

    urls = _parse_gtfs_urls()
    if not urls:
        logger.warning("Keine OEPNV_GTFS_URLS gesetzt. Import wird uebersprungen.")
        _release_import_lock()
        return

    try:
        municipality_signature = _prepare_staging()

        loaded_feeds = 0
        active_stage_keys: list[str] = []
        for idx, url in enumerate(urls):
            feed_key = f"f{idx}"
            schema_base = f"oepnv_gtfs_f{idx}"

            try:
                gtfs_path = _download_gtfs(url)
                raw_imported = False
                registry_row = _get_feed_registry(feed_key)
                active_schema_name = registry_row[0] if registry_row else schema_base

                if _should_import_gtfs(feed_key, gtfs_path):
                    import_schema_name = f"{schema_base}_{int(time.time())}"
                    _import_gtfs_to_postgres(gtfs_path, import_schema_name)
                    _store_feed_registry(feed_key, gtfs_path, import_schema_name)
                    active_schema_name = import_schema_name
                    raw_imported = True
                else:
                    logger.info("GTFS-Rohimport uebersprungen, Feed unveraendert: %s", gtfs_path)

                if raw_imported or _should_rebuild_staging(feed_key, municipality_signature):
                    active_stage_key = f"{feed_key}:{int(time.time())}"
                    logger.info("Starte GTFS-Staging fuer %s mit stage key %s", feed_key, active_stage_key)
                    _load_feed_into_staging(active_stage_key, active_schema_name)
                    _store_stage_registry(feed_key, municipality_signature, active_stage_key)
                else:
                    logger.info("GTFS-Staging uebersprungen, Feed und Gemeinden unveraendert: %s", feed_key)
                    stage_registry = _get_stage_registry(feed_key)
                    if stage_registry and stage_registry[1]:
                        active_stage_key = stage_registry[1]
                    else:
                        raise RuntimeError(f"Kein aktiver GTFS-Stage-Key fuer {feed_key} vorhanden")
                active_stage_keys.append(active_stage_key)
                loaded_feeds += 1
            except Exception as exc:
                logger.warning("GTFS-Verarbeitung fehlgeschlagen (%s): %s", url, exc)
                continue

        if loaded_feeds == 0:
            logger.warning("Kein GTFS-Feed erfolgreich verarbeitet. Kein Write.")
            return

        stop_density_values, departures_values, regularity_values = _compute_metrics(active_stage_keys)

        _write_indicator(
            key="oepnv_stop_density",
            name="OEPNV-Haltestellendichte",
            category="oepnv",
            unit="stops_per_10k",
            direction="higher_is_better",
            normalization_mode="log",
            methodology=(
                "GTFS-CSV-Dateien werden direkt nach PostgreSQL geladen. Haltestellen werden der naechsten "
                "Gemeindegeometrie via PostGIS zugeordnet, mit Zentroid-Fallback ausserhalb der Polygonflaechen, "
                "ueber Koordinaten dedupliziert und je 10.000 Einwohner normiert."
            ),
            values=stop_density_values,
        )

        _write_indicator(
            key="oepnv_departures_per_10k",
            name="OEPNV-Abfahrtsdichte",
            category="oepnv",
            unit="departures_per_10k",
            direction="higher_is_better",
            normalization_mode="log",
            methodology=(
                "GTFS stop_times/trips/calendar werden in PostGIS per SQL aggregiert. "
                "Service-Kalender wird als Wochenanteilsgewicht genutzt; Ergebnis je 10.000 Einwohner auf Gemeindeebene."
            ),
            values=departures_values,
        )

        _write_indicator(
            key="oepnv_departure_regularity",
            name="OEPNV-Abfahrtsregelmaessigkeit",
            category="oepnv",
            unit="index_0_100",
            direction="higher_is_better",
            normalization_mode="linear",
            methodology=(
                "Regelmaessigkeitsindex aus 15-Minuten-Bins pro Haltestelle auf Basis von GTFS stop_times in SQL. "
                "Aggregation je Gemeinde gewichtet mit Abfahrtsvolumen."
            ),
            values=regularity_values,
        )

        logger.info(
            "OEPNV-Import abgeschlossen (Feeds=%s, Stops=%s Regionen, Abfahrten=%s Regionen, Regelmaessigkeit=%s Regionen)",
            loaded_feeds,
            len(stop_density_values),
            len(departures_values),
            len(regularity_values),
        )
    finally:
        _release_import_lock()


if __name__ == "__main__":
    main()

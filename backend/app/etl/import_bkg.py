import logging
import json
import re
import time
from collections.abc import Iterable
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import bindparam, delete
from sqlalchemy import text as sa_text
from sqlmodel import Session, select

from app.core.ars import normalize_ars, slugify_region_name
from app.core.config import settings
from app.core.db import engine, check_schema_drift
from app.models.indicator import RegionIndicatorValue
from app.models.region import Region
from app.models.score import RegionScoreSnapshot

logger = logging.getLogger("etl.import_bkg")
logging.basicConfig(level=logging.INFO)

BKG_WFS_URL = "https://sgx.geodatenzentrum.de/wfs_vg250-ew"
XREPOSITORY_AGS_URN = "urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:ags"
XREPOSITORY_AGS_DETAILS_URL = (
    "https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:ags"
)
XREPOSITORY_AGS_API_URL = (
    "https://www.xrepository.de/api/xrepository/"
    "urn%3Ade%3Abund%3Adestatis%3Abevoelkerungsstatistik%3Aschluessel%3Aags"
)
XREPOSITORY_KREIS_URN = "urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:kreis_2025-03-31"
XREPOSITORY_KREIS_DETAILS_URL = (
    "https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:kreis_2025-03-31"
)
XREPOSITORY_KREIS_JSON_URL = (
    "https://www.xrepository.de/api/xrepository/"
    "urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:kreis_2025-03-31/"
    "download/Kreis_2025-03-31.json"
)
WFS_VERSION = "2.0.0"
WFS_PAGE_SIZE = 5000
WIKIDATA_BATCH_SIZE = 50
WIKIDATA_REQUEST_RETRIES = 3
WIKIDATA_RETRY_DELAY_SECONDS = 2.0
STATE_NAMES = {
    "01": "Schleswig-Holstein",
    "02": "Hamburg",
    "03": "Niedersachsen",
    "04": "Bremen",
    "05": "Nordrhein-Westfalen",
    "06": "Hessen",
    "07": "Rheinland-Pfalz",
    "08": "Baden-Wuerttemberg",
    "09": "Bayern",
    "10": "Saarland",
    "11": "Berlin",
    "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern",
    "14": "Sachsen",
    "15": "Sachsen-Anhalt",
    "16": "Thueringen",
}


def _chunked[T](items: list[T], size: int) -> Iterable[list[T]]:
    for start_idx in range(0, len(items), size):
        yield items[start_idx: start_idx + size]


def _normalize_property_key(raw: str) -> str:
    return raw.split(":")[-1].lower()


def _sql_identifier(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", normalized):
        raise ValueError(f"Ungueltiger SQL-Identifier: {value}")
    return normalized


def _qualified_table_name(value: str) -> tuple[str, str]:
    normalized = _sql_identifier(value)
    if "." in normalized:
        schema, table = normalized.split(".", 1)
    else:
        schema, table = "public", normalized
    return schema, table


def _column_names(session: Session, schema: str, table: str) -> set[str]:
    rows = session.execute(
        sa_text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    ).fetchall()
    return {str(row[0]) for row in rows}


def _resolve_geometry_flavour(session: Session, schema: str, table: str, preferred: int) -> int:
    values = session.execute(
        sa_text(
            f"""
            SELECT DISTINCT gf
            FROM {schema}.{table}
            WHERE gf IS NOT NULL
            ORDER BY gf
            """
        )
    ).fetchall()
    flavours = [int(row[0]) for row in values]
    if not flavours:
        return preferred
    if preferred in flavours:
        return preferred
    if len(flavours) == 1:
        logger.warning(
            "BKG-Tabelle %s.%s enthaelt kein gf=%s, verwende automatisch gf=%s.",
            schema,
            table,
            preferred,
            flavours[0],
        )
        return flavours[0]
    raise RuntimeError(
        f"BKG-Tabelle {schema}.{table} enthaelt nicht den konfigurierten gf={preferred}. "
        f"Vorhanden sind: {', '.join(str(value) for value in flavours)}"
    )


def _get_prop(props: dict[str, Any], candidates: list[str]) -> Any | None:
    for key in candidates:
        if key in props and props[key] not in (None, ""):
            return props[key]
    return None


def _flatten_coords(value: Any) -> tuple[float, float, float, float] | None:
    if isinstance(value, list):
        if value and isinstance(value[0], (int, float)) and len(value) >= 2:
            lon = float(value[0])
            lat = float(value[1])
            return lat, lat, lon, lon
        bounds = [_flatten_coords(item) for item in value]
        bounds = [item for item in bounds if item]
        if not bounds:
            return None
        min_lat = min(item[0] for item in bounds)
        max_lat = max(item[1] for item in bounds)
        min_lon = min(item[2] for item in bounds)
        max_lon = max(item[3] for item in bounds)
        return min_lat, max_lat, min_lon, max_lon
    return None


def _centroid_from_geometry(geometry: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if not geometry:
        return None, None
    coords = geometry.get("coordinates")
    bounds = _flatten_coords(coords)
    if not bounds:
        return None, None
    min_lat, max_lat, min_lon, max_lon = bounds
    return round((min_lat + max_lat) / 2, 6), round((min_lon + max_lon) / 2, 6)


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except ValueError:
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _state_name_from_code(code: str | None) -> str:
    if not code:
        return "Unbekannt"
    return STATE_NAMES.get(code, "Unbekannt")


def _district_name_from_props(props: dict[str, Any]) -> str | None:
    value = _get_prop(
        props,
        [
            "gen_krs",
            "krs_name",
            "kreis_name",
            "landkreis",
            "name_krs",
            "gen_kreis",
            "kreis",
            "bez_krs",
        ],
    )
    if value is None:
        return None
    district_name = str(value).strip()
    return district_name or None


def _district_column_name(available_columns: set[str]) -> str | None:
    for column in [
        "gen_krs",
        "krs_name",
        "kreis_name",
        "landkreis",
        "name_krs",
        "gen_kreis",
        "kreis",
        "bez_krs",
    ]:
        if column in available_columns:
            return column
    return None


def fetch_xrepository_ags_metadata() -> dict[str, str] | None:
    try:
        response = httpx.get(XREPOSITORY_AGS_API_URL, timeout=30.0)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
    except Exception as exc:
        logger.warning(
            "XRepository AGS-Metadatenabruf fehlgeschlagen: %s", exc)
        return None

    versions = [
        (elem.text or "").strip()
        for elem in root.findall(".//{*}versionCodeliste.kennung")
        if (elem.text or "").strip()
    ]
    latest_version_urn = versions[-1] if versions else XREPOSITORY_AGS_URN
    latest_version = latest_version_urn.rsplit(
        "_", 1)[-1] if "_" in latest_version_urn else ""

    return {
        "urn": XREPOSITORY_AGS_URN,
        "latest_version_urn": latest_version_urn,
        "latest_version": latest_version,
        "source_url": XREPOSITORY_AGS_DETAILS_URL,
    }


def _element_text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _parse_genericode_columns(root: ElementTree.Element) -> dict[str, str]:
    columns: dict[str, str] = {}
    for column in root.findall(".//{*}Column"):
        column_id = column.attrib.get("Id") or column.attrib.get("id")
        if not column_id:
            continue
        short_name = _element_text(column.find(".//{*}ShortName"))
        long_name = _element_text(column.find(".//{*}LongName"))
        canonical_uri = _element_text(column.find(".//{*}CanonicalUri"))
        identifier = short_name or long_name or canonical_uri or column_id
        columns[column_id] = identifier.upper()
    return columns


def _value_texts(element: ElementTree.Element) -> list[str]:
    texts: list[str] = []
    for child in element.iter():
        if child.text is None:
            continue
        value = child.text.strip()
        if value:
            texts.append(value)
    return texts


def _parse_genericode_rows(xml_text: str) -> dict[str, str]:
    root = ElementTree.fromstring(xml_text)
    column_names = _parse_genericode_columns(root)
    district_names: dict[str, str] = {}
    for row in root.findall(".//{*}Row"):
        values: dict[str, str] = {}
        for value in row.findall(".//{*}Value"):
            column_ref = value.attrib.get(
                "ColumnRef") or value.attrib.get("columnRef")
            if not column_ref:
                continue
            value_text_candidates = _value_texts(value)
            simple_value = next(
                (candidate for candidate in value_text_candidates if candidate), None)
            if simple_value:
                values[column_names.get(
                    column_ref, column_ref).upper()] = simple_value
        if not values:
            continue
        code = next(
            (
                values[key]
                for key in [
                    "SCHLUESSEL",
                    "CODE",
                    "KEY",
                    "IDENTIFIER",
                    "EMPFOHLENE CODESPALTE",
                ]
                if key in values and re.fullmatch(r"\d{5}", values[key])
            ),
            None,
        )
        if not code:
            code = next((value for value in values.values()
                        if re.fullmatch(r"\d{5}", value)), None)
        name = next(
            (
                values[key]
                for key in [
                    "BEZEICHNUNG",
                    "NAME",
                    "GEN",
                    "LANGNAME",
                    "KURZNAME",
                ]
                if key in values and values[key]
            ),
            None,
        )
        if not name:
            text_candidates = [
                value
                for value in values.values()
                if value
                and not re.fullmatch(r"\d{5}", value)
                and not value.lower().startswith("urn:")
                and "http" not in value.lower()
                and re.search(r"[A-Za-zÄÖÜäöüß]", value)
            ]
            if text_candidates:
                name = max(text_candidates, key=len)
        if code and name:
            district_names[code] = name.strip()
    return district_names


def fetch_xrepository_kreis_mapping() -> dict[str, str]:
    try:
        response = httpx.get(XREPOSITORY_KREIS_JSON_URL, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        mapping: dict[str, str] = {}
        if isinstance(payload, dict) and isinstance(payload.get("daten"), list) and isinstance(payload.get("spalten"), list):
            columns = [
                (
                    str(column.get("spaltennameTechnisch")
                        or column.get("spaltennameLang") or "")
                    .strip()
                    .upper()
                )
                for column in payload["spalten"]
                if isinstance(column, dict)
            ]
            code_index = next(
                (index for index, name in enumerate(
                    columns) if name == "SCHLUESSEL"),
                None,
            )
            name_index = next(
                (index for index, name in enumerate(columns)
                 if name in {"BEZEICHNUNG", "NAME", "GEN"}),
                None,
            )
            if code_index is not None and name_index is not None:
                for row in payload["daten"]:
                    if not isinstance(row, list):
                        continue
                    if max(code_index, name_index) >= len(row):
                        continue
                    code = str(row[code_index]).strip(
                    ) if row[code_index] is not None else ""
                    name = str(row[name_index]).strip(
                    ) if row[name_index] is not None else ""
                    if re.fullmatch(r"\d{5}", code) and name:
                        mapping[code] = name
        elif isinstance(payload, list):
            for row in payload:
                if not isinstance(row, dict):
                    continue
                code = next(
                    (
                        str(row.get(key)).strip()
                        for key in ["SCHLUESSEL", "schluessel", "code", "CODE", "id", "ID"]
                        if row.get(key) is not None and re.fullmatch(r"\d{5}", str(row.get(key)).strip())
                    ),
                    None,
                )
                name = next(
                    (
                        str(row.get(key)).strip()
                        for key in ["BEZEICHNUNG", "bezeichnung", "NAME", "name", "GEN", "gen"]
                        if row.get(key) not in (None, "")
                    ),
                    None,
                )
                if code and name:
                    mapping[code] = name
        if mapping:
            logger.info(
                "Kreis-Referenz aus XRepository geladen (%s Eintraege)", len(mapping))
            return mapping
        logger.warning(
            "XRepository Kreisreferenz lieferte keine parsebaren JSON-Eintraege.")
        return {}
    except Exception as exc:
        logger.warning(
            "XRepository Kreisreferenzabruf fehlgeschlagen: %s", exc)
        return {}


def apply_xrepository_district_names(rows: list[dict[str, object]], district_mapping: dict[str, str]) -> None:
    if not district_mapping:
        return
    for row in rows:
        district_name = row.get("district_name")
        if district_name not in (None, ""):
            continue
        ars = normalize_ars(str(row["ars"]))
        district_code = ars[:5] if len(ars) >= 5 else None
        if not district_code:
            continue
        mapped_name = district_mapping.get(district_code)
        if mapped_name:
            row["district_name"] = mapped_name


def assign_unique_slugs(rows: list[dict[str, object]]) -> None:
    seen: dict[str, str] = {}
    for row in sorted(rows, key=lambda item: str(item.get("ars", ""))):
        base_slug = slugify_region_name(
            str(row["name"]),
            str(row.get("district_name", "")),
            str(row.get("state_name", "")),
            str(row.get("bem", "")),
            str(row.get("_district_type", "")),
        )
        ars_value = normalize_ars(str(row["ars"]))
        slug = base_slug
        if slug in seen and seen[slug] != ars_value:
            slug = f"{base_slug}-{ars_value}"
        row["_slug"] = slug
        seen[slug] = ars_value


def upsert_regions(session: Session, rows: Iterable[dict[str, object]]) -> None:
    count = 0
    for row in rows:
        region_row = {key: value for key,
                      value in row.items() if not key.startswith("_")}
        ars_value = normalize_ars(str(region_row["ars"]))
        region_row["ars"] = ars_value
        region_row["slug"] = str(row.get("_slug") or slugify_region_name(
            str(region_row["name"]),
            str(region_row.get("district_name", "")),
            str(region_row.get("state_name", "")),
            str(region_row.get("bem", "")),
            str(row.get("_district_type", "")),
        ))

        existing = session.exec(select(Region).where(
            Region.ars == ars_value)).first()
        if existing:
            for key, value in region_row.items():
                setattr(existing, key, value)
            session.add(existing)
        else:
            session.add(Region(**region_row))
        count += 1
        if count % 1000 == 0:
            logger.info("Regionen verarbeitet: %s", count)
    session.commit()
    logger.info("Regionen upserted: %s", count)


def ensure_boundary_table(session: Session) -> None:
    session.exec(
        sa_text(
            """
            CREATE SCHEMA IF NOT EXISTS geo;
            """
        )
    )
    session.exec(
        sa_text(
            """
            CREATE TABLE IF NOT EXISTS geo.municipality_boundary (
                ags text PRIMARY KEY,
                geom geometry(MultiPolygon, 4326) NOT NULL
            );
            """
        )
    )
    session.exec(
        sa_text(
            """
            CREATE TABLE IF NOT EXISTS geo.state_boundary (
                state_code text PRIMARY KEY,
                state_name text NOT NULL,
                geom geometry(MultiPolygon, 4326) NOT NULL
            );
            """
        )
    )
    session.exec(
        sa_text(
            """
            CREATE INDEX IF NOT EXISTS municipality_boundary_geom_idx
            ON geo.municipality_boundary
            USING gist (geom);
            """
        )
    )
    session.exec(
        sa_text(
            """
            CREATE INDEX IF NOT EXISTS state_boundary_geom_idx
            ON geo.state_boundary
            USING gist (geom);
            """
        )
    )
    session.commit()


def upsert_municipality_boundaries(session: Session, rows: Iterable[dict[str, object]]) -> None:
    ensure_boundary_table(session)
    target_ags: set[str] = set()
    for row in rows:
        target_ags.add(str(row["ars"]))
        geometry_json = row.get("_geometry_json")
        if not geometry_json:
            continue
        session.execute(
            sa_text(
                """
                INSERT INTO geo.municipality_boundary (ags, geom)
                VALUES (
                    :ags,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry_json), 4326))
                )
                ON CONFLICT (ags) DO UPDATE
                SET geom = EXCLUDED.geom;
                """
            ),
            {
                "ags": str(row["ars"]),
                "geometry_json": str(geometry_json),
            },
        )
    if target_ags:
        session.execute(
            sa_text(
                """
                DELETE FROM geo.municipality_boundary
                WHERE ags NOT IN :target_ags;
                """
            ).bindparams(bindparam("target_ags", expanding=True)),
            {"target_ags": sorted(target_ags)},
        )
    session.commit()


def refresh_state_boundaries(session: Session) -> None:
    ensure_boundary_table(session)
    session.execute(sa_text("TRUNCATE geo.state_boundary"))
    session.execute(
        sa_text(
            """
            INSERT INTO geo.state_boundary (state_code, state_name, geom)
            SELECT
                r.state_code,
                MAX(r.state_name) AS state_name,
                ST_Multi(ST_Union(b.geom)) AS geom
            FROM geo.municipality_boundary b
            JOIN region r
              ON r.ars = b.ags
            GROUP BY r.state_code
            """
        )
    )
    session.commit()


def prune_non_target_regions(session: Session, target_ags: set[str]) -> int:
    regions = list(session.exec(select(Region.id, Region.ars)))
    stale_ids = [region_id for region_id,
                 ars in regions if ars not in target_ags]
    if not stale_ids:
        return 0

    session.exec(delete(RegionIndicatorValue).where(
        RegionIndicatorValue.region_id.in_(stale_ids)))
    session.exec(delete(RegionScoreSnapshot).where(
        RegionScoreSnapshot.region_id.in_(stale_ids)))
    session.exec(delete(Region).where(Region.id.in_(stale_ids)))
    session.commit()
    return len(stale_ids)


def _get_capabilities() -> str:
    params = {"service": "WFS",
              "request": "GetCapabilities", "version": WFS_VERSION}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(BKG_WFS_URL, params=params)
        response.raise_for_status()
        return response.text


def _extract_typenames_from_capabilities(xml_text: str) -> list[str]:
    root = ElementTree.fromstring(xml_text)
    names: list[str] = []
    for element in root.iter():
        if element.tag.endswith("Name") and element.text:
            text = element.text.strip()
            if text and "gem" in text.lower() and text not in names:
                names.append(text)
    return names


def _fetch_features_page(type_name: str, start_index: int, count: int) -> list[dict[str, Any]]:
    params = {
        "service": "WFS",
        "version": WFS_VERSION,
        "request": "GetFeature",
        "typeNames": type_name,
        "srsName": "EPSG:4326",
        "outputFormat": "application/json",
        "count": str(count),
        "startIndex": str(start_index),
        "cql_filter": f"gf={settings.bkg_geometry_flavour}",
    }
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        response = client.get(BKG_WFS_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    return payload.get("features", [])


def _fetch_features_all(type_name: str, count: int = WFS_PAGE_SIZE) -> list[dict[str, Any]]:
    start_index = 0
    out: list[dict[str, Any]] = []
    while True:
        page = _fetch_features_page(
            type_name, start_index=start_index, count=count)
        if not page:
            break
        out.extend(page)
        logger.info("WFS %s: %s Features geladen (startIndex=%s)",
                    type_name, len(page), start_index)
        if len(page) < count:
            break
        start_index += count
    return out


def _geometry_json(feature: dict[str, Any]) -> str | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None
    try:
        return json.dumps(geometry)
    except TypeError:
        return None


def _wikipedia_title_candidates(row: dict[str, object]) -> list[str]:
    name = str(row["name"]).strip()
    state_name = str(row["state_name"]).strip()
    candidates = [name]
    candidates.append(f"{name} ({state_name})")
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _build_wikidata_url(wikidata_id: str | None) -> str | None:
    if not wikidata_id:
        return None
    return f"https://www.wikidata.org/wiki/{wikidata_id}"


def _build_sparql_query(article_titles: list[str]) -> str:
    wikipedia_project_url = f"https://{settings.wikipedia_language}.wikipedia.org/"
    title_values = " ".join(
        f"{json.dumps(title)}@{settings.wikipedia_language}" for title in article_titles)
    return f"""
    PREFIX schema: <http://schema.org/>

    SELECT ?article_title ?item ?article
    WHERE {{
      VALUES ?article_title {{ {title_values} }}
      ?article schema:isPartOf <{wikipedia_project_url}> ;
               schema:name ?article_title ;
               schema:about ?item .
    }}
    """


def _fetch_wikidata_pages(title_to_ags: dict[str, str]) -> dict[str, dict[str, str | None]]:
    if not title_to_ags:
        return {}

    result: dict[str, dict[str, str | None]] = {}
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "wohnortkompass-etl/1.0",
    }

    with httpx.Client(timeout=120, follow_redirects=True, headers=headers) as client:
        titles = sorted(title_to_ags)
        for title_batch in _chunked(titles, WIKIDATA_BATCH_SIZE):
            response = None
            for attempt in range(1, WIKIDATA_REQUEST_RETRIES + 1):
                response = client.get(
                    settings.wikidata_sparql_url,
                    params={"query": _build_sparql_query(title_batch)},
                )
                if response.status_code not in {429, 502, 503, 504}:
                    response.raise_for_status()
                    break

                retry_after = response.headers.get("Retry-After")
                delay_seconds = float(
                    retry_after) if retry_after else WIKIDATA_RETRY_DELAY_SECONDS * attempt
                logger.warning(
                    "Wikidata transient error %s for batch of %s titles, retry %s/%s after %.1fs",
                    response.status_code,
                    len(title_batch),
                    attempt,
                    WIKIDATA_REQUEST_RETRIES,
                    delay_seconds,
                )
                time.sleep(delay_seconds)
            else:
                logger.warning(
                    "Wikidata batch skipped after repeated transient failures (%s titles)", len(title_batch))
                continue

            payload = response.json()
            for binding in payload.get("results", {}).get("bindings", []):
                article_title = binding.get("article_title", {}).get("value")
                item_url = binding.get("item", {}).get("value")
                article_url = binding.get("article", {}).get("value")
                if not article_title or not item_url:
                    continue
                ags_code = title_to_ags.get(article_title)
                if not ags_code:
                    continue
                wikidata_id = item_url.rstrip("/").split("/")[-1]
                result[ags_code] = {
                    "wikidata_id": wikidata_id,
                    "wikidata_url": _build_wikidata_url(wikidata_id),
                    "wikipedia_url": article_url,
                }
            logger.info(
                "Wikidata/Wikipedia-Enrichment geladen fuer %s Titel", len(title_batch))

    return result


def enrich_rows_with_wikidata(rows: list[dict[str, object]]) -> None:
    links_by_ags: dict[str, dict[str, str | None]] = {}
    try:
        initial_title_to_ags = {_wikipedia_title_candidates(
            row)[0]: str(row["ars"]) for row in rows}
        links_by_ags.update(_fetch_wikidata_pages(initial_title_to_ags))
    except Exception as exc:
        logger.warning(
            "Wikidata-Enrichment fuer Primartitel fehlgeschlagen: %s", exc)

    unresolved_rows = [row for row in rows if str(
        row["ars"]) not in links_by_ags]
    if unresolved_rows:
        try:
            fallback_title_to_ags: dict[str, str] = {}
            for row in unresolved_rows:
                candidates = _wikipedia_title_candidates(row)
                for candidate in candidates[1:]:
                    fallback_title_to_ags[candidate] = str(row["ars"])
            links_by_ags.update(_fetch_wikidata_pages(fallback_title_to_ags))
        except Exception as exc:
            logger.warning(
                "Wikidata-Enrichment fuer Fallbacktitel fehlgeschlagen: %s", exc)

    for row in rows:
        link_data = links_by_ags.get(str(row["ars"]), {})
        row["wikidata_id"] = link_data.get("wikidata_id")
        row["wikidata_url"] = link_data.get("wikidata_url")
        row["wikipedia_url"] = link_data.get("wikipedia_url")


def _row_from_feature(feature: dict[str, Any]) -> dict[str, object] | None:
    raw_props = feature.get("properties") or {}
    props = {_normalize_property_key(k): v for k, v in raw_props.items()}
    if _safe_int(props.get("gf")) != settings.bkg_geometry_flavour:
        return None

    ags = _get_prop(
        props,
        [
            "ags",
            "ars",
            "rs",
            "schluessel",
            "gemeindeschluessel",
            "ags_0",
            "ars_0",
        ],
    )
    if not ags:
        return None

    ags_str = normalize_ars(str(ags).strip())
    if len(ags_str) != 8:
        return None

    name = _get_prop(props, ["gen", "name", "gemeinde_name",
                     "bezeichnung"]) or f"Gemeinde {ags_str}"
    state_code = str(
        _get_prop(props, ["sn_l", "state_code"]) or ags_str[:2]).zfill(2)
    state_name = str(_get_prop(
        props, ["gen_land", "land_name"]) or _state_name_from_code(state_code))
    district_name = _district_name_from_props(props)

    ew = _safe_int(_get_prop(props, ["ewz", "ew", "einwohner"]))
    area = _safe_float(_get_prop(props, ["kfl", "flaeche", "shape_area"]))
    if area and area > 50000:
        area = round(area / 1_000_000, 2)

    lat, lon = _centroid_from_geometry(feature.get("geometry"))

    return {
        "ars": ags_str,
        "name": str(name),
        "level": "gemeinde",
        "state_code": state_code,
        "state_name": state_name,
        "district_name": district_name,
        "population": ew,
        "area_km2": area,
        "centroid_lat": lat,
        "centroid_lon": lon,
        "_geometry_json": _geometry_json(feature),
    }


def fetch_bkg_districts_from_postgis(session: Session) -> dict[str, dict[str, str]]:
    schema, table = _qualified_table_name(settings.bkg_district_table)
    geometry_flavour = _resolve_geometry_flavour(
        session, schema, table, settings.bkg_geometry_flavour
    )

    sql = sa_text(
        f"""
        SELECT
            ags,
            gen AS district_name,
            bez AS district_type,
            LPAD(COALESCE(CAST(sn_l AS text), SUBSTRING(ags FROM 1 FOR 2)), 2, '0') AS state_code
        FROM {schema}.{table}
        WHERE ags IS NOT NULL
          AND gf = :geometry_flavour
        ORDER BY ags
        """
    )

    records = session.execute(
        sql,
        {"geometry_flavour": geometry_flavour},
    ).mappings().all()

    logger.info("Gefundene Kreise in BKG-Tabelle %s.%s: %s", schema, table, len(records))
    district_rows: dict[str, dict[str, str]] = {}
    for record in records:
        district_ags = normalize_ars(str(record["ags"]).strip())
        district_code = district_ags[:5] if len(district_ags) >= 5 else ""
        if len(district_code) != 5:
            continue
        district_rows[district_code] = {
            "district_name": str(record["district_name"]).strip() if record["district_name"] else "",
            "district_type": str(record["district_type"]).strip() if record["district_type"] else "",
            "state_code": str(record["state_code"]).zfill(2) if record["state_code"] else "",
        }
    return district_rows


def fetch_bkg_regions_from_postgis(session: Session) -> list[dict[str, object]]:
    schema, table = _qualified_table_name(settings.bkg_municipality_table)
    geometry_column = _sql_identifier(settings.bkg_geometry_column)
    available_columns = _column_names(session, schema, table)
    geometry_flavour = _resolve_geometry_flavour(
        session, schema, table, settings.bkg_geometry_flavour)
    population_column = next(
        (column for column in ["ewz", "ew", "einwohner",
         "population"] if column in available_columns),
        None,
    )
    area_column = next(
        (column for column in ["kfl", "flaeche", "shape_area",
         "area_km2"] if column in available_columns),
        None,
    )
    district_column = _district_column_name(available_columns)
    population_expr = f"{population_column} AS population" if population_column else "NULL::bigint AS population"
    area_expr = (
        f"{area_column} AS area_km2"
        if area_column
        else f"ROUND(CAST(ST_Area({geometry_column}::geography) / 1000000.0 AS numeric), 2) AS area_km2"
    )
    district_expr = f"{district_column} AS district_name" if district_column else "NULL::text AS district_name"
    sql = sa_text(
        f"""
        SELECT
            ags,
            bem,
            gen AS name,
            LPAD(COALESCE(CAST(sn_l AS text), SUBSTRING(ags FROM 1 FOR 2)), 2, '0') AS state_code,
            {district_expr},
            {population_expr},
            {area_expr},
            ROUND(CAST(ST_Y(ST_Centroid({geometry_column})) AS numeric), 6) AS centroid_lat,
            ROUND(CAST(ST_X(ST_Centroid({geometry_column})) AS numeric), 6) AS centroid_lon,
            ST_AsGeoJSON(ST_Multi(ST_Force2D({geometry_column}))) AS geometry_json
        FROM {schema}.{table}
        WHERE ags IS NOT NULL
          AND gf = :geometry_flavour
          AND {geometry_column} IS NOT NULL
        ORDER BY ags
        """
    )
    records = session.execute(
        sql,
        {"geometry_flavour": geometry_flavour},
    ).mappings().all()
    district_rows = fetch_bkg_districts_from_postgis(session)
    rows: list[dict[str, object]] = []
    for record in records:
        ags_str = normalize_ars(str(record["ags"]).strip())
        if len(ags_str) != 8:
            continue
        state_code = str(record["state_code"]).zfill(2)
        district_code = ags_str[:5]
        district_data = district_rows.get(district_code, {})
        rows.append(
            {
                "ars": ags_str,
                "bem": str(record["bem"]).strip() if record["bem"] else None,
                "name": str(record["name"] or f"Gemeinde {ags_str}"),
                "level": "gemeinde",
                "state_code": state_code,
                "state_name": _state_name_from_code(state_code),
                "district_name": district_data.get("district_name")
                or (str(record["district_name"]).strip() if record["district_name"] else None),
                "_district_type": district_data.get("district_type") or None,
                "population": _safe_int(record["population"]),
                "area_km2": _safe_float(record["area_km2"]),
                "centroid_lat": _safe_float(record["centroid_lat"]),
                "centroid_lon": _safe_float(record["centroid_lon"]),
                "_geometry_json": str(record["geometry_json"]) if record["geometry_json"] else None,
            }
        )
    return rows


def fetch_bkg_regions() -> list[dict[str, object]]:
    district_mapping = fetch_xrepository_kreis_mapping()
    with Session(engine) as session:
        try:
            rows = fetch_bkg_regions_from_postgis(session)
            if rows:
                apply_xrepository_district_names(rows, district_mapping)
                assign_unique_slugs(rows)
                logger.info(
                    "BKG Gemeinde-Import erfolgreich aus PostGIS-Tabelle %s (gf=%s, %s Gemeinden)",
                    settings.bkg_municipality_table,
                    settings.bkg_geometry_flavour,
                    len(rows),
                )
                return rows
            logger.warning(
                "BKG PostGIS-Tabelle %s lieferte keine Gemeinden mit gf=%s. Fallback auf WFS.",
                settings.bkg_municipality_table,
                settings.bkg_geometry_flavour,
            )
        except Exception as exc:
            logger.warning(
                "BKG PostGIS-Import aus %s fehlgeschlagen: %s. Fallback auf WFS.",
                settings.bkg_municipality_table,
                exc,
            )

    candidates = [
        "vg250-ew:vg250_gem",
        "vg250:vg250_gem",
        "vg250_ew:vg250_gem",
        "vg250:gem",
        "vg250-ew:gem",
        "vg250:GEM",
        "vg250-ew:GEM",
    ]

    try:
        capabilities = _get_capabilities()
        discovered = _extract_typenames_from_capabilities(capabilities)
        for name in discovered:
            if name not in candidates:
                candidates.append(name)
    except Exception as exc:
        logger.warning("GetCapabilities fehlgeschlagen: %s", exc)

    errors: list[str] = []
    for type_name in candidates:
        try:
            features = _fetch_features_all(type_name)
            if not features:
                continue
            rows = [_row_from_feature(feature) for feature in features]
            rows = [row for row in rows if row is not None]
            if rows:
                apply_xrepository_district_names(rows, district_mapping)
                assign_unique_slugs(rows)
                logger.info(
                    "BKG WFS Gemeinde-Import erfolgreich mit Layer %s (%s Gemeinden)", type_name, len(rows))
                return rows
        except Exception as exc:
            errors.append(f"{type_name}: {exc}")

    if errors:
        logger.warning(
            "BKG WFS Layer-Versuche fehlgeschlagen: %s", " | ".join(errors))
    return []


def main() -> None:
    logger.info("BKG-Import gestartet (Ziel: alle Gemeinden per AGS)")
    ags_reference = fetch_xrepository_ags_metadata()
    if ags_reference:
        logger.info(
            "AGS-Referenz aus XRepository geladen (urn=%s, version=%s)",
            ags_reference["urn"],
            ags_reference["latest_version"] or ags_reference["latest_version_urn"],
        )
    if not check_schema_drift():
        logger.warning(
            "Schema drift detected during BKG import. Import may fail or produce incorrect results. "
            "Run alembic migrations to fix schema issues."
        )
    rows = fetch_bkg_regions()
    if not rows:
        logger.error(
            "BKG-WFS Gemeindeimport fehlgeschlagen. Keine Demo-Daten mehr als Fallback.")
        return
    enrich_rows_with_wikidata(rows)

    with Session(engine) as session:
        target_ags = {str(row["ars"]) for row in rows}
        removed = prune_non_target_regions(session, target_ags)
        if removed:
            logger.info("Legacy/Non-Target Regionen entfernt: %s", removed)
        upsert_regions(session, rows)
        logger.info("Regionen upserted, beginne mit Geometrieimport...")
        upsert_municipality_boundaries(session, rows)
        refresh_state_boundaries(session)

    logger.info("BKG-Import abgeschlossen (%s Gemeinden)", len(rows))


if __name__ == "__main__":
    main()

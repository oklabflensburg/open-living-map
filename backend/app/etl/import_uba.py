import logging
import re
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text
from sqlmodel import select

from app.core.config import settings
from app.etl.common import (
    clear_indicator_values,
    get_or_create_indicator,
    normalize,
    tracked_etl_run,
    with_session,
)
from app.models.indicator import RegionIndicatorValue
from app.models.region import Region

logger = logging.getLogger("etl.import_uba")
logging.basicConfig(level=logging.INFO)

UBA_BASE = "https://luftdaten.umweltbundesamt.de/api/air-data/v4"
ENV_IT_STATION_BASE = "https://www.env-it.de/stationen/public/station.do"
STATION_CODE_PATTERN = re.compile(r"^DE[A-Z]{2,}\d{2,}$")


def _nearest_station_value(
    municipality_lat: float,
    municipality_lon: float,
    station_values: list[tuple[float, float, float]],
) -> float | None:
    best_value: float | None = None
    best_dist = float("inf")
    for station_lat, station_lon, station_value in station_values:
        dist = (municipality_lat - station_lat) ** 2 + (municipality_lon - station_lon) ** 2
        if dist < best_dist:
            best_dist = dist
            best_value = station_value
    return best_value


def _nearest_station(
    municipality_lat: float,
    municipality_lon: float,
    station_values: list[tuple[str, float, float, float]],
) -> tuple[str, float] | None:
    best_station_id: str | None = None
    best_value: float | None = None
    best_dist = float("inf")
    for station_id, station_lat, station_lon, station_value in station_values:
        dist = (municipality_lat - station_lat) ** 2 + (municipality_lon - station_lon) ** 2
        if dist < best_dist:
            best_dist = dist
            best_station_id = station_id
            best_value = station_value
    if best_station_id is None or best_value is None:
        return None
    return best_station_id, best_value


def _fetch_stations() -> dict[str, list[str]]:
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(f"{UBA_BASE}/stations/json")
        response.raise_for_status()
        payload = response.json()
    return payload.get("data", {})


def _first_station_code(row: list[object]) -> str | None:
    for value in row:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if STATION_CODE_PATTERN.match(candidate):
            return candidate
    return None


def _guess_station_name(station_id: str, row: list[object]) -> str:
    code = _first_station_code(row)
    for value in row:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if not candidate or candidate == code:
            continue
        if candidate.isdigit():
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}$", candidate):
            continue
        if candidate.startswith("http"):
            continue
        return candidate
    return f"Station {station_id}"


def _build_station_page_url(station_code: str | None) -> str | None:
    if not station_code:
        return None
    return f"{ENV_IT_STATION_BASE}?selectedStationcode={station_code}"


def _build_station_measures_url(station_id: str) -> str:
    today = datetime.now(UTC).date().isoformat()
    return (
        "https://www.umweltbundesamt.de/api/air_data/v4/measures/json"
        f"?lang=de&date_from={today}&time_from=1&date_to={today}&time_to=24&station={station_id}"
    )


def ensure_uba_station_table(session) -> None:
    session.execute(text("CREATE SCHEMA IF NOT EXISTS air"))
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS air.region_air_station (
                region_ars text NOT NULL,
                indicator_key text NOT NULL,
                station_id text NOT NULL,
                station_code text NULL,
                station_name text NOT NULL,
                latitude double precision NULL,
                longitude double precision NULL,
                station_page_url text NULL,
                measures_url text NOT NULL,
                PRIMARY KEY (region_ars, indicator_key)
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS region_air_station_region_idx
            ON air.region_air_station (region_ars)
            """
        )
    )
    session.commit()


def _write_region_air_stations(
    session,
    *,
    indicator_key: str,
    assignments: list[tuple[str, str]],
    station_metadata: dict[str, dict[str, object]],
) -> None:
    ensure_uba_station_table(session)
    session.execute(
        text("DELETE FROM air.region_air_station WHERE indicator_key = :indicator_key"),
        {"indicator_key": indicator_key},
    )
    rows: list[dict[str, object]] = []
    for region_ars, station_id in assignments:
        metadata = station_metadata.get(station_id)
        if not metadata:
            continue
        rows.append(
            {
                "region_ars": region_ars,
                "indicator_key": indicator_key,
                "station_id": station_id,
                "station_code": metadata.get("station_code"),
                "station_name": metadata.get("station_name"),
                "latitude": metadata.get("latitude"),
                "longitude": metadata.get("longitude"),
                "station_page_url": metadata.get("station_page_url"),
                "measures_url": metadata.get("measures_url"),
            }
        )
    if rows:
        session.execute(
            text(
                """
                INSERT INTO air.region_air_station (
                    region_ars,
                    indicator_key,
                    station_id,
                    station_code,
                    station_name,
                    latitude,
                    longitude,
                    station_page_url,
                    measures_url
                ) VALUES (
                    :region_ars,
                    :indicator_key,
                    :station_id,
                    :station_code,
                    :station_name,
                    :latitude,
                    :longitude,
                    :station_page_url,
                    :measures_url
                )
                """
            ),
            rows,
        )
    session.commit()


def _fetch_measures(
    component_id: int, days: int = 7
) -> dict[str, dict[str, list[float | int | None | str]]]:
    date_to = datetime.now(UTC).date()
    date_from = date_to - timedelta(days=days)
    params = {
        "date_from": date_from.isoformat(),
        "time_from": "00:00",
        "date_to": date_to.isoformat(),
        "time_to": "23:00",
        "component": str(component_id),
    }
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        response = client.get(f"{UBA_BASE}/measures/json", params=params)
        response.raise_for_status()
        payload = response.json()
    return payload.get("data", {})


def _fetch_measures_with_fallback(
    component_id: int,
) -> dict[str, dict[str, list[float | int | None | str]]]:
    for days in [7, 3, 1]:
        try:
            return _fetch_measures(component_id, days=days)
        except Exception as exc:
            logger.warning(
                "UBA measures fallback fuer component=%s, days=%s fehlgeschlagen: %s",
                component_id,
                days,
                exc,
            )
    return {}


def _mean_station_values(
    measures_data: dict[str, dict[str, list[float | int | None | str]]],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for station_id, entries in measures_data.items():
        vals: list[float] = []
        for value in entries.values():
            if not isinstance(value, list) or len(value) < 3:
                continue
            measured = value[2]
            if measured is None:
                continue
            try:
                measured_float = float(measured)
            except (TypeError, ValueError):
                continue
            if measured_float <= -900:
                continue
            vals.append(measured_float)
        if vals:
            out[station_id] = sum(vals) / len(vals)
    return out


def _batch_write_indicator_values(
    session,
    *,
    indicator_id: int,
    period: str,
    values: list[tuple[int, float]],
    normalized_values: list[float],
    quality_flag: str,
) -> None:
    existing_rows = {
        row.region_id: row
        for row in session.exec(
            select(RegionIndicatorValue).where(
                RegionIndicatorValue.indicator_id == indicator_id,
                RegionIndicatorValue.period == period,
            )
        )
    }

    for (municipality_id, raw), normalized in zip(values, normalized_values, strict=True):
        existing = existing_rows.get(municipality_id)
        if existing:
            existing.raw_value = round(raw, 4)
            existing.normalized_value = normalized
            existing.quality_flag = quality_flag
            session.add(existing)
            continue

        session.add(
            RegionIndicatorValue(
                region_id=municipality_id,
                indicator_id=indicator_id,
                period=period,
                raw_value=round(raw, 4),
                normalized_value=normalized,
                quality_flag=quality_flag,
            )
        )


def main() -> None:
    logger.info("UBA-Import gestartet")
    with tracked_etl_run(
        job_name="import_uba",
        sources=[
            {"source_name": "UBA air data API", "source_url": f"{UBA_BASE}/doc"},
            {"source_name": "Env-it station pages", "source_url": ENV_IT_STATION_BASE},
        ],
    ) as run:
        with with_session() as session:
            municipalities = list(session.exec(select(Region).where(Region.level == "gemeinde")))
            municipality_coords = [
                (
                    municipality.id,
                    municipality.ars,
                    float(municipality.centroid_lat),
                    float(municipality.centroid_lon),
                )
                for municipality in municipalities
                if municipality.centroid_lat is not None and municipality.centroid_lon is not None
            ]
            if not municipality_coords:
                logger.warning(
                    "Keine Gemeinde-Zentroide verfuegbar. UBA-Import wird uebersprungen."
                )
                return

            try:
                stations = _fetch_stations()
            except Exception as exc:
                logger.warning("UBA Stationsabruf fehlgeschlagen: %s", exc)
                return

            station_positions: dict[str, tuple[float, float]] = {}
            station_metadata: dict[str, dict[str, object]] = {}
            for station_id, row in stations.items():
                if not isinstance(row, list) or len(row) < 9:
                    continue
                try:
                    lon = float(row[7])
                    lat = float(row[8])
                except (TypeError, ValueError):
                    continue
                station_positions[station_id] = (lat, lon)
                station_code = _first_station_code(row)
                station_metadata[station_id] = {
                    "station_id": station_id,
                    "station_code": station_code,
                    "station_name": _guess_station_name(station_id, row),
                    "latitude": lat,
                    "longitude": lon,
                    "station_page_url": _build_station_page_url(station_code),
                    "measures_url": _build_station_measures_url(station_id),
                }

            if not station_positions:
                logger.warning("Keine verwertbaren UBA-Stationen gefunden. Kein Write.")
                return

            # component ids laut UBA components/json
            defs = [
                ("no2", "NO2", 5),
                ("pm10", "PM10", 1),
                ("pm25", "PM2.5", 9),
            ]

            rows_written = 0
            for key, name, component_id in defs:
                measures_data = _fetch_measures_with_fallback(component_id)
                if not measures_data:
                    logger.warning("UBA Measures fuer %s fehlgeschlagen.", key)
                    continue

                station_means = _mean_station_values(measures_data)
                positioned_station_values = [
                    (
                        station_id,
                        station_positions[station_id][0],
                        station_positions[station_id][1],
                        value,
                    )
                    for station_id, value in station_means.items()
                    if station_id in station_positions
                ]
                if not positioned_station_values:
                    logger.warning("UBA-Indikator %s ohne Stationen mit Koordinaten.", key)
                    continue

                values = [
                    (municipality_id, nearest_value)
                    for municipality_id, _, municipality_lat, municipality_lon in municipality_coords
                    for nearest in [
                        _nearest_station(
                            municipality_lat, municipality_lon, positioned_station_values
                        )
                    ]
                    if nearest is not None
                    for _, nearest_value in [nearest]
                ]
                if not values:
                    logger.warning("UBA-Indikator %s ohne verwertbare Werte.", key)
                    continue

                station_assignments = [
                    (region_ars, station_id)
                    for _, region_ars, municipality_lat, municipality_lon in municipality_coords
                    for nearest in [
                        _nearest_station(
                            municipality_lat, municipality_lon, positioned_station_values
                        )
                    ]
                    if nearest is not None
                    for station_id, _ in [nearest]
                ]

                indicator = get_or_create_indicator(
                    session,
                    key=key,
                    name=name,
                    category="air",
                    unit="ug/m3",
                    direction="lower_is_better",
                    normalization_mode="robust_percentile",
                    source_name="Umweltbundesamt Luftdaten API v4",
                    source_url="https://luftdaten.umweltbundesamt.de/api/air-data/v4/doc",
                    methodology=(
                        "Messwerte der letzten Tage je Station, dann Zuordnung jeder Gemeinde "
                        "zur naechsten UBA-Messstation auf AGS-Ebene."
                    ),
                )
                clear_indicator_values(
                    session,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                )

                raw_values = [raw for _, raw in values]
                normalized_values = normalize(
                    raw_values, "lower_is_better", mode="robust_percentile"
                )
                _batch_write_indicator_values(
                    session,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                    values=values,
                    normalized_values=normalized_values,
                    quality_flag="nearest_station_proxy",
                )
                _write_region_air_stations(
                    session,
                    indicator_key=key,
                    assignments=station_assignments,
                    station_metadata=station_metadata,
                )
                rows_written += len(values)
                logger.info("UBA-Indikator %s geschrieben: %s Gemeinden", key, len(values))

            session.commit()
            run.set_rows_written(rows_written)

    logger.info("UBA-Import abgeschlossen")


if __name__ == "__main__":
    main()

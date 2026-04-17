import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import httpx
from sqlmodel import select

from app.core.config import settings
from app.etl.common import (
    clear_indicator_values,
    get_or_create_indicator,
    normalize,
    with_session,
)
from app.models.indicator import RegionIndicatorValue
from app.models.region import Region

logger = logging.getLogger("etl.import_uba")
logging.basicConfig(level=logging.INFO)

UBA_BASE = "https://luftdaten.umweltbundesamt.de/api/air-data/v4"


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


def _fetch_stations() -> dict[str, list[str]]:
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(f"{UBA_BASE}/stations/json")
        response.raise_for_status()
        payload = response.json()
    return payload.get("data", {})


def _fetch_measures(component_id: int, days: int = 7) -> dict[str, dict[str, list[float | int | None | str]]]:
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


def _fetch_measures_with_fallback(component_id: int) -> dict[str, dict[str, list[float | int | None | str]]]:
    for days in [7, 3, 1]:
        try:
            return _fetch_measures(component_id, days=days)
        except Exception as exc:
            logger.warning("UBA measures fallback fuer component=%s, days=%s fehlgeschlagen: %s", component_id, days, exc)
    return {}


def _mean_station_values(measures_data: dict[str, dict[str, list[float | int | None | str]]]) -> dict[str, float]:
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

    for (municipality_id, raw), normalized in zip(values, normalized_values):
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
    with with_session() as session:
        municipalities = list(session.exec(select(Region).where(Region.level == "gemeinde")))
        municipality_coords = [
            (municipality.id, float(municipality.centroid_lat), float(municipality.centroid_lon))
            for municipality in municipalities
            if municipality.centroid_lat is not None and municipality.centroid_lon is not None
        ]
        if not municipality_coords:
            logger.warning("Keine Gemeinde-Zentroide verfuegbar. UBA-Import wird uebersprungen.")
            return

        try:
            stations = _fetch_stations()
        except Exception as exc:
            logger.warning("UBA Stationsabruf fehlgeschlagen: %s", exc)
            return

        station_positions: dict[str, tuple[float, float]] = {}
        for station_id, row in stations.items():
            if not isinstance(row, list) or len(row) < 9:
                continue
            try:
                lon = float(row[7])
                lat = float(row[8])
            except (TypeError, ValueError):
                continue
            station_positions[station_id] = (lat, lon)

        if not station_positions:
            logger.warning("Keine verwertbaren UBA-Stationen gefunden. Kein Write.")
            return

        # component ids laut UBA components/json
        defs = [
            ("no2", "NO2", 5),
            ("pm10", "PM10", 1),
            ("pm25", "PM2.5", 9),
        ]

        for key, name, component_id in defs:
            measures_data = _fetch_measures_with_fallback(component_id)
            if not measures_data:
                logger.warning("UBA Measures fuer %s fehlgeschlagen.", key)
                continue

            station_means = _mean_station_values(measures_data)
            positioned_station_values = [
                (station_positions[station_id][0], station_positions[station_id][1], value)
                for station_id, value in station_means.items()
                if station_id in station_positions
            ]
            if not positioned_station_values:
                logger.warning("UBA-Indikator %s ohne Stationen mit Koordinaten.", key)
                continue

            values = [
                (municipality_id, nearest_value)
                for municipality_id, municipality_lat, municipality_lon in municipality_coords
                for nearest_value in [_nearest_station_value(municipality_lat, municipality_lon, positioned_station_values)]
                if nearest_value is not None
            ]
            if not values:
                logger.warning("UBA-Indikator %s ohne verwertbare Werte.", key)
                continue

            indicator = get_or_create_indicator(
                session,
                key=key,
                name=name,
                category="air",
                unit="ug/m3",
                direction="lower_is_better",
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
            normalized_values = normalize(raw_values, "lower_is_better")
            _batch_write_indicator_values(
                session,
                indicator_id=indicator.id,
                period=settings.default_score_period,
                values=values,
                normalized_values=normalized_values,
                quality_flag="nearest_station_proxy",
            )

            logger.info("UBA-Indikator %s geschrieben: %s Gemeinden", key, len(values))

        session.commit()

    logger.info("UBA-Import abgeschlossen")


if __name__ == "__main__":
    main()

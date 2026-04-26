import io
import logging
import re
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlmodel import select

from app.core.config import settings
from app.etl.common import (
    clear_indicator_values,
    download_file,
    get_or_create_indicator,
    normalize,
    tracked_etl_run,
    with_session,
)
from app.models.indicator import RegionIndicatorValue
from app.models.region import Region

logger = logging.getLogger("etl.import_dwd")
logging.basicConfig(level=logging.INFO)


def _should_refresh_recent_file(path: Path) -> bool:
    if not path.exists():
        return True

    max_age = timedelta(hours=settings.dwd_recent_cache_max_age_hours)
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return datetime.now(UTC) - modified_at >= max_age


def _download_recent_file(url: str, target: Path, *, timeout: int) -> Path:
    return download_file(
        url,
        target,
        timeout=timeout,
        force=_should_refresh_recent_file(target),
    )


def _nearest_station_metrics(
    municipality_lat: float,
    municipality_lon: float,
    station_metrics: list[tuple[str, str, float, float, tuple[float, float, float]]],
) -> tuple[str, str, float, float, tuple[float, float, float]] | None:
    best_match: tuple[str, str, float, float, tuple[float, float, float]] | None = None
    best_dist = float("inf")
    for station_id, station_name, station_lat, station_lon, metrics in station_metrics:
        dist = (municipality_lat - station_lat) ** 2 + (municipality_lon - station_lon) ** 2
        if dist < best_dist:
            best_dist = dist
            best_match = (station_id, station_name, station_lat, station_lon, metrics)
    return best_match


def _write_region_climate_stations(
    session,
    *,
    assignments: list[dict[str, object]],
) -> None:
    session.execute(text("DELETE FROM climate.region_climate_station"))
    if assignments:
        session.execute(
            text(
                """
            INSERT INTO climate.region_climate_station (
                region_ars,
                indicator_key,
                station_id,
                station_name,
                latitude,
                longitude,
                source_url
            ) VALUES (
                :region_ars,
                :indicator_key,
                :station_id,
                :station_name,
                :latitude,
                :longitude,
                :source_url
            )
            """
            ),
            assignments,
        )
    session.commit()


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


def _parse_station_file(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="latin1", errors="ignore")
    lines = [line for line in text.splitlines() if line.strip()]
    payload = "\n".join(lines[2:])
    df = pd.read_fwf(io.StringIO(payload), header=None)
    if df.shape[1] < 6:
        return pd.DataFrame()
    df = df.rename(
        columns={
            0: "station_id",
            1: "from_date",
            2: "to_date",
            3: "elevation",
            4: "lat",
            5: "lon",
            6: "station_name",
            7: "state",
        }
    )
    df["station_id"] = pd.to_numeric(df["station_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["station_id"])
    df["station_id"] = df["station_id"].astype(int).astype(str).str.zfill(5)
    df["to_date"] = pd.to_datetime(df["to_date"], format="%Y%m%d", errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df.dropna(subset=["lat", "lon"])


def _recent_station_ids() -> list[str]:
    url = f"{settings.dwd_base_url}/recent/"
    import httpx

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    ids = re.findall(r"tageswerte_KL_([0-9]{5})_akt\.zip", html)
    return sorted(set(ids))


def _read_station_zip(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as zf:
        product_files = [name for name in zf.namelist() if name.startswith("produkt_klima_tag")]
        if not product_files:
            return pd.DataFrame()
        with zf.open(product_files[0]) as handle:
            df = pd.read_csv(handle, sep=";", low_memory=False)

    df.columns = [str(col).strip() for col in df.columns]
    for col in ["TXK", "RSK"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "MESS_DATUM" in df.columns:
        df["MESS_DATUM"] = pd.to_datetime(
            df["MESS_DATUM"].astype(str), format="%Y%m%d", errors="coerce"
        )
    return df


def _station_metrics(
    df: pd.DataFrame, lookback_days: int = 365
) -> tuple[float, float, float] | None:
    if (
        df.empty
        or "MESS_DATUM" not in df.columns
        or "TXK" not in df.columns
        or "RSK" not in df.columns
    ):
        return None

    cutoff = pd.Timestamp(datetime.now(UTC).date() - timedelta(days=lookback_days))
    valid = df[df["MESS_DATUM"] >= cutoff].copy()
    if valid.empty:
        return None

    txk = valid["TXK"].where(valid["TXK"] > -900).dropna()
    rsk = valid["RSK"].where(valid["RSK"] > -900).dropna()
    if txk.empty:
        return None

    heat_days = float((txk >= 30.0).sum())
    summer_days = float((txk >= 25.0).sum())
    precipitation_proxy = float(rsk.sum()) if not rsk.empty else 0.0
    return heat_days, summer_days, precipitation_proxy


def main() -> None:
    logger.info("DWD-Import gestartet")
    station_file = settings.raw_data_path / "dwd" / "KL_Tageswerte_Beschreibung_Stationen.txt"
    station_url = f"{settings.dwd_base_url}/recent/KL_Tageswerte_Beschreibung_Stationen.txt"

    with tracked_etl_run(
        job_name="import_dwd",
        sources=[
            {"source_name": "DWD stations", "source_url": station_url},
            {"source_name": "DWD daily climate", "source_url": settings.dwd_base_url},
        ],
    ) as run:
        try:
            _download_recent_file(station_url, station_file, timeout=120)
        except Exception as exc:
            logger.warning("DWD Stationsdatei nicht ladbar, Import wird uebersprungen: %s", exc)
            return

        stations_df = _parse_station_file(station_file)
        if stations_df.empty:
            logger.warning("DWD Stationsdatei konnte nicht geparst werden. Kein Write.")
            return

        active_ids = set(_recent_station_ids())
        stations_df = stations_df[stations_df["station_id"].isin(active_ids)]
        if settings.dwd_max_stations > 0:
            stations_df = stations_df.head(settings.dwd_max_stations)
        if stations_df.empty:
            logger.warning("Keine aktiven DWD-Stationen gefunden. Kein Write.")
            return

        with with_session() as session:
            municipalities = list(session.exec(select(Region).where(Region.level == "gemeinde")))
            municipality_by_id = {municipality.id: municipality for municipality in municipalities}
            municipality_coords = [
                (
                    municipality.id,
                    float(municipality.centroid_lat),
                    float(municipality.centroid_lon),
                )
                for municipality in municipalities
                if municipality.centroid_lat is not None and municipality.centroid_lon is not None
            ]
            if not municipality_coords:
                logger.warning("Keine Gemeinde-Zentroide verfuegbar. Kein Write.")
                return

            station_metrics: list[tuple[str, str, float, float, tuple[float, float, float]]] = []

            for _, station in stations_df.iterrows():
                station_id = str(station["station_id"])
                station_name = str(station.get("station_name") or f"Station {station_id}").strip()
                lat = float(station["lat"])
                lon = float(station["lon"])

                zip_name = f"tageswerte_KL_{station_id}_akt.zip"
                target = settings.raw_data_path / "dwd" / "recent" / zip_name
                url = f"{settings.dwd_base_url}/recent/{zip_name}"
                try:
                    _download_recent_file(url, target, timeout=120)
                except Exception:
                    continue

                station_data = _read_station_zip(target)
                metrics = _station_metrics(station_data)
                if metrics is None:
                    continue

                station_metrics.append((station_id, station_name, lat, lon, metrics))

            if not station_metrics:
                logger.warning(
                    "Keine verwertbaren DWD-Stationen mit Metriken gefunden. Kein Write."
                )
                return

            per_municipality: dict[int, dict[str, list[float]]] = {}
            climate_station_assignments: list[dict[str, object]] = []
            for municipality_id, municipality_lat, municipality_lon in municipality_coords:
                match = _nearest_station_metrics(
                    municipality_lat, municipality_lon, station_metrics
                )
                if match is None:
                    continue
                station_id, station_name, station_lat, station_lon, metrics = match
                heat_days, summer_days, precipitation_proxy = metrics
                per_municipality[municipality_id] = {
                    "heat_days": [heat_days],
                    "summer_days": [summer_days],
                    "precipitation_proxy": [precipitation_proxy],
                }
                region = municipality_by_id.get(municipality_id)
                if region is None:
                    continue
                for indicator_key in ("heat_days", "summer_days", "precipitation_proxy"):
                    climate_station_assignments.append(
                        {
                            "region_ars": region.ars,
                            "indicator_key": indicator_key,
                            "station_id": station_id,
                            "station_name": station_name,
                            "latitude": station_lat,
                            "longitude": station_lon,
                            "source_url": "https://opendata.dwd.de/",
                        }
                    )

            indicator_defs = [
                ("heat_days", "Hitzetage", "count", "lower_is_better"),
                ("summer_days", "Sommertage", "count", "higher_is_better"),
                ("precipitation_proxy", "Niederschlag", "mm", "higher_is_better"),
            ]

            for key, name, unit, direction in indicator_defs:
                values = [
                    (municipality_id, float(sum(vals[key]) / len(vals[key])))
                    for municipality_id, vals in per_municipality.items()
                    if vals[key]
                ]
                if not values:
                    logger.warning("DWD-Indikator %s ohne verwertbare Werte, uebersprungen.", key)
                    continue

                indicator = get_or_create_indicator(
                    session,
                    key=key,
                    name=name,
                    category="climate",
                    unit=unit,
                    direction=direction,
                    normalization_mode="robust_percentile",
                    source_name="DWD CDC Daily KL",
                    source_url="https://opendata.dwd.de/",
                    methodology=(
                        "Stationsdaten (aktuell) werden je Station ausgewertet und ueber die naechste "
                        "DWD-Station jeder Gemeindezentroid-Zuordnung auf AGS-Ebene zugewiesen."
                    ),
                )
                clear_indicator_values(
                    session,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                )

                raw_values = [raw for _, raw in values]
                normalized_values = normalize(raw_values, direction, mode="robust_percentile")
                _batch_write_indicator_values(
                    session,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                    values=values,
                    normalized_values=normalized_values,
                    quality_flag="nearest_station_proxy",
                )

            _write_region_climate_stations(
                session,
                assignments=climate_station_assignments,
            )
            session.commit()
            run.set_rows_written(len(per_municipality))

        logger.info(
            "DWD-Import abgeschlossen (%s Gemeinden mit DWD-Zuordnung)", len(per_municipality)
        )


if __name__ == "__main__":
    main()

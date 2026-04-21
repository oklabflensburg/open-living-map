import io
import json
import logging
import zipfile
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlmodel import select

from app.core.ars import normalize_ars
from app.core.config import settings
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
from app.models.region import Region

configure_logging()
logger = logging.getLogger("etl.import_unfallatlas")

UNFALLATLAS_BASE_URL = "https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/"
ACCIDENT_CATEGORY_KEYS = {
    1: "killed",
    2: "seriously_injured",
    3: "slightly_injured",
}
CITY_STATE_AGGREGATE_AGS = {
    "02": "02000000",
    "11": "11000000",
}


def _bounded_normalized_score(value: float) -> float:
    return round(min(99.9, max(0.1, value)), 2)


def _latest_csv_zip_name() -> str | None:
    import httpx

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(UNFALLATLAS_BASE_URL)
        response.raise_for_status()
        payload = response.json()

    latest_year = -1
    latest_name: str | None = None
    for dataset in payload.get("datasets", []):
        name = str(dataset.get("name", ""))
        if not name.startswith("Unfallorte"):
            continue
        try:
            year = int(name.replace("Unfallorte", ""))
        except ValueError:
            continue

        for file_info in dataset.get("files", []):
            file_name = str(file_info.get("name", ""))
            if file_name.endswith("_CSV.zip") and year > latest_year:
                latest_year = year
                latest_name = file_name

    return latest_name


def _download_latest_csv_zip() -> Path | None:
    file_name = _latest_csv_zip_name()
    if not file_name:
        return None

    target = settings.raw_data_path / "unfallatlas" / file_name
    url = f"{UNFALLATLAS_BASE_URL}{file_name}"
    try:
        return download_file(url, target, timeout=180)
    except Exception as exc:
        logger.warning("Unfallatlas Download fehlgeschlagen: %s", exc)
        return None


def _read_unfallatlas_csv(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_files = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not csv_files:
            return pd.DataFrame()
        with zf.open(csv_files[0]) as handle:
            raw = handle.read()

    # Quelle nutzt semikolon-separierte CSV mit deutschem Dezimalformat.
    df = pd.read_csv(
        io.BytesIO(raw),
        sep=";",
        encoding="utf-8",
        decimal=",",
        low_memory=False,
    )
    return df


def _to_region_ars(df: pd.DataFrame) -> pd.Series:
    for col in ["ULAND", "UREGBEZ", "UKREIS", "UGEMEINDE"]:
        if col not in df.columns:
            raise ValueError(f"Pflichtspalte {col} fehlt in Unfallatlas CSV")

    land = pd.to_numeric(df["ULAND"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(2)
    reg = pd.to_numeric(df["UREGBEZ"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(1)
    district = pd.to_numeric(df["UKREIS"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(2)
    municipality = pd.to_numeric(df["UGEMEINDE"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(3)
    ars8 = land + reg + district + municipality
    kreisfreie_mask = municipality == "000"
    ars8 = ars8.where(~kreisfreie_mask, (land + reg + district + "000"))
    for state_code, aggregate_ags in CITY_STATE_AGGREGATE_AGS.items():
        ars8 = ars8.where(land != state_code, aggregate_ags)
    return ars8.map(normalize_ars)


def ensure_unfallatlas_tables(session) -> None:
    session.execute(text("CREATE SCHEMA IF NOT EXISTS traffic"))
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS traffic.accident_point (
                accident_id text NOT NULL,
                region_ars text NOT NULL,
                category text NOT NULL,
                year integer NOT NULL,
                geom geometry(Point, 4326) NOT NULL,
                PRIMARY KEY (accident_id, region_ars)
            )
            """
        )
    )
    has_old_column = session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'traffic'
                  AND table_name = 'accident_point'
                  AND column_name = 'district_ars'
            )
            """
        )
    ).scalar()
    has_new_column = session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'traffic'
                  AND table_name = 'accident_point'
                  AND column_name = 'region_ars'
            )
            """
        )
    ).scalar()
    if has_old_column and not has_new_column:
        session.execute(text("ALTER TABLE traffic.accident_point RENAME COLUMN district_ars TO region_ars"))
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS accident_point_geom_idx
            ON traffic.accident_point
            USING gist (geom)
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS accident_point_region_category_idx
            ON traffic.accident_point (region_ars, category)
            """
        )
    )
    session.commit()


def _write_accident_points(session, df: pd.DataFrame) -> None:
    ensure_unfallatlas_tables(session)
    session.execute(text("TRUNCATE traffic.accident_point"))

    rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        region_ars = normalize_ars(str(getattr(row, "ars")))
        if not region_ars:
            continue
        lon = getattr(row, "XGCSWGS84", None)
        lat = getattr(row, "YGCSWGS84", None)
        if pd.isna(lon) or pd.isna(lat):
            continue
        category = ACCIDENT_CATEGORY_KEYS.get(int(getattr(row, "UKATEGORIE", 0) or 0))
        if not category:
            continue
        rows.append(
            {
                "accident_id": str(getattr(row, "UIDENTSTLAE")),
                "region_ars": region_ars,
                "category": category,
                "year": int(getattr(row, "UJAHR")),
                "lon": float(lon),
                "lat": float(lat),
            }
        )

    if rows:
        session.execute(
            text(
                """
                INSERT INTO traffic.accident_point (accident_id, region_ars, category, year, geom)
                VALUES (
                    :accident_id,
                    :region_ars,
                    :category,
                    :year,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
                """
            ),
            rows,
        )
    session.commit()


def main() -> None:
    logger.info("Unfallatlas-Import gestartet")
    with tracked_etl_run(
        job_name="import_unfallatlas",
        sources=[
            {
                "source_name": "Destatis Unfallatlas",
                "source_url": "https://www.destatis.de/DE/Service/Statistik-Visualisiert/unfall-atlas.html",
            }
        ],
    ) as run:
        zip_path = _download_latest_csv_zip()
        if zip_path is None:
            logger.warning("Keine Unfallatlas CSV-ZIP gefunden. Import wird beendet.")
            return

        df = _read_unfallatlas_csv(zip_path)
        if df.empty:
            logger.warning("Unfallatlas CSV leer oder nicht lesbar. Kein Write.")
            return

        try:
            df["ars"] = _to_region_ars(df)
        except ValueError as exc:
            logger.warning("Unfallatlas-Spalten unerwartet: %s", exc)
            return

        # Jeder Datensatz ist ein Unfallort-Ereignis, daher count je Gemeinde.
        agg = df.groupby("ars", as_index=False).size().rename(columns={"size": "accidents_total"})

        with with_session() as session:
            regions = list(session.exec(select(Region)))
            region_by_ars = {region.ars: region for region in regions}

            rows: list[tuple[int, float]] = []
            for _, row in agg.iterrows():
                ars = str(row["ars"])
                region = region_by_ars.get(ars)
                if region is None:
                    continue
                rows.append((region.id, float(row["accidents_total"])))

            if not rows:
                logger.warning("Unfallatlas-Daten konnten auf keine Region gemappt werden. Kein Write.")
                return

            _write_accident_points(session, df)

            indicator = get_or_create_indicator(
                session,
                key="road_accidents_total",
                name="Verkehrsunfaelle gesamt",
                category="safety",
                unit="count",
                direction="lower_is_better",
                normalization_mode="log",
                source_name="Destatis Unfallatlas",
                source_url="https://www.destatis.de/DE/Service/Statistik-Visualisiert/unfall-atlas.html",
                methodology=(
                    "Unfallorte-CSV (aktuellstes Jahr) wird je Gemeinde aggregiert; "
                    "Gemeindezuordnung ueber ULAND/UREGBEZ/UKREIS/UGEMEINDE -> AGS; "
                    "Normierung logarithmisch mit leichtem Floor/Ceiling, damit keine exakten 0.0 oder 100.0 entstehen."
                ),
            )
            clear_indicator_values(
                session,
                indicator_id=indicator.id,
                period=settings.default_score_period,
            )

            raw_values = [raw for _, raw in rows]
            normalized_values = [
                _bounded_normalized_score(value)
                for value in normalize(raw_values, indicator.direction, mode="log")
            ]
            for (region_id, raw), norm in zip(rows, normalized_values):
                upsert_region_indicator_value(
                    session,
                    region_id=region_id,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                    raw_value=round(raw, 4),
                    normalized_value=norm,
                    quality_flag="ok",
                )

            run.set_rows_written(len(rows))
            logger.info("Unfallatlas-Import abgeschlossen (%s Regionen)", len(rows))


if __name__ == "__main__":
    main()

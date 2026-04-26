import logging
import math
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import SchemaDriftError, assert_schema_is_current, engine
from app.core.logging import configure_logging
from app.models.etl import EtlRun, EtlRunSource
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from app.models.region import Region

configure_logging()
logger = logging.getLogger("etl")


@dataclass
class EtlRunTracker:
    job_name: str
    sources: list[dict[str, str | None]] = field(default_factory=list)
    rows_written: int | None = None

    def set_rows_written(self, rows_written: int | None) -> None:
        self.rows_written = rows_written

    def add_source(
        self,
        *,
        source_name: str,
        source_url: str | None = None,
        source_version: str | None = None,
        source_hash: str | None = None,
    ) -> None:
        self.sources.append(
            {
                "source_name": source_name,
                "source_url": source_url,
                "source_version": source_version,
                "source_hash": source_hash,
            }
        )


@contextmanager
def tracked_etl_run(
    job_name: str,
    *,
    sources: list[dict[str, str | None]] | None = None,
) -> Any:
    tracker = EtlRunTracker(job_name=job_name, sources=list(sources or []))
    run_id: int | None = None
    start_time = datetime.utcnow()

    with Session(engine) as session:
        run = EtlRun(job_name=job_name, status="running", started_at=start_time)
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

        for source in tracker.sources:
            session.add(
                EtlRunSource(
                    etl_run_id=run_id,
                    source_name=str(source["source_name"]),
                    source_url=source.get("source_url"),
                    source_version=source.get("source_version"),
                    source_hash=source.get("source_hash"),
                )
            )
        session.commit()

    try:
        yield tracker
    except Exception as exc:
        with Session(engine) as session:
            run = session.get(EtlRun, run_id)
            if run:
                run.status = "failed"
                run.rows_written = tracker.rows_written
                run.error_message = str(exc)[:4000]
                run.finished_at = datetime.utcnow()
                session.add(run)
                session.commit()
        raise
    else:
        with Session(engine) as session:
            run = session.get(EtlRun, run_id)
            if run:
                run.status = "completed"
                run.rows_written = tracker.rows_written
                run.finished_at = datetime.utcnow()
                session.add(run)
                session.commit()


def ensure_dirs() -> None:
    settings.raw_data_path.mkdir(parents=True, exist_ok=True)
    settings.staging_data_path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, target: Path, timeout: int = 60, force: bool = False) -> Path:
    ensure_dirs()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        logger.info("Download uebersprungen, Datei bereits vorhanden: %s", target)
        return target
    logger.info("Download: %s", url)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        target.write_bytes(response.content)
    return target


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)


def get_regions(session: Session) -> list[Region]:
    return list(session.exec(select(Region)))


def get_or_create_indicator(
    session: Session,
    *,
    key: str,
    name: str,
    category: str,
    unit: str,
    direction: str,
    normalization_mode: str = "log",
    source_name: str,
    source_url: str,
    methodology: str,
) -> IndicatorDefinition:
    existing = session.exec(
        select(IndicatorDefinition).where(IndicatorDefinition.key == key)
    ).first()
    if existing:
        existing.name = name
        existing.category = category
        existing.unit = unit
        existing.direction = direction
        existing.normalization_mode = normalization_mode
        existing.source_name = source_name
        existing.source_url = source_url
        existing.methodology = methodology
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    indicator = IndicatorDefinition(
        key=key,
        name=name,
        category=category,
        unit=unit,
        direction=direction,
        normalization_mode=normalization_mode,
        source_name=source_name,
        source_url=source_url,
        methodology=methodology,
    )
    session.add(indicator)
    session.commit()
    session.refresh(indicator)
    return indicator


def upsert_region_indicator_value(
    session: Session,
    *,
    region_id: int,
    indicator_id: int,
    period: str,
    raw_value: float,
    normalized_value: float,
    quality_flag: str = "ok",
) -> RegionIndicatorValue:
    existing = session.exec(
        select(RegionIndicatorValue)
        .where(RegionIndicatorValue.region_id == region_id)
        .where(RegionIndicatorValue.indicator_id == indicator_id)
        .where(RegionIndicatorValue.period == period)
    ).first()

    if existing:
        existing.raw_value = raw_value
        existing.normalized_value = normalized_value
        existing.quality_flag = quality_flag
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = RegionIndicatorValue(
        region_id=region_id,
        indicator_id=indicator_id,
        period=period,
        raw_value=raw_value,
        normalized_value=normalized_value,
        quality_flag=quality_flag,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def clear_indicator_values(session: Session, *, indicator_id: int, period: str) -> None:
    session.exec(
        delete(RegionIndicatorValue).where(
            RegionIndicatorValue.indicator_id == indicator_id,
            RegionIndicatorValue.period == period,
        )
    )
    session.commit()


def _min_max_scale(values: list[float], direction: str) -> list[float]:
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [50.0 for _ in values]

    scaled = [((value - min_val) / (max_val - min_val)) * 100 for value in values]
    if direction == "lower_is_better":
        scaled = [100 - value for value in scaled]
    return [round(value, 2) for value in scaled]


def _log_transform(values: list[float]) -> list[float]:
    min_val = min(values)
    if min_val < 0:
        offset = abs(min_val) + 1.0
        return [math.log(value + offset) for value in values]
    return [math.log1p(value) for value in values]


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("sorted_values must not be empty")
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * percentile
    lower_index = int(math.floor(rank))
    upper_index = int(math.ceil(rank))
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = rank - lower_index
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


def _robust_percentile_scale(values: list[float], direction: str) -> list[float]:
    if not values:
        return []
    sorted_values = sorted(values)
    lower = _percentile(sorted_values, 0.05)
    upper = _percentile(sorted_values, 0.95)
    if upper == lower:
        return [50.0 for _ in values]

    clipped = [min(max(value, lower), upper) for value in values]
    return _min_max_scale(clipped, direction)


def normalize(values: list[float], direction: str, mode: str = "log") -> list[float]:
    if mode == "linear":
        return _min_max_scale(values, direction)
    if mode == "log":
        return _min_max_scale(_log_transform(values), direction)
    if mode == "robust_percentile":
        return _robust_percentile_scale(values, direction)
    raise ValueError(f"Unknown normalization mode: {mode}")


def normalize_log(values: list[float], direction: str) -> list[float]:
    return normalize(values, direction, mode="log")


def normalize_linear(values: list[float], direction: str) -> list[float]:
    return normalize(values, direction, mode="linear")


def normalize_robust_percentile(values: list[float], direction: str) -> list[float]:
    return normalize(values, direction, mode="robust_percentile")


def with_session() -> Session:
    """Get database session for ETL operations after validating schema state."""
    try:
        assert_schema_is_current()
    except SchemaDriftError:
        logger.exception("ETL aborted because the database schema is outdated.")
        raise
    return Session(engine)

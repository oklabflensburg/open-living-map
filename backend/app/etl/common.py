import logging
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from sqlmodel import Session, select
from sqlalchemy import delete

from app.core.config import settings
from app.core.db import engine
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from app.models.region import Region

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("etl")


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
    source_name: str,
    source_url: str,
    methodology: str,
) -> IndicatorDefinition:
    existing = session.exec(select(IndicatorDefinition).where(IndicatorDefinition.key == key)).first()
    if existing:
        existing.name = name
        existing.category = category
        existing.unit = unit
        existing.direction = direction
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


def normalize(values: list[float], direction: str) -> list[float]:
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


def with_session() -> Session:
    return Session(engine)

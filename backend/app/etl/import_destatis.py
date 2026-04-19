import csv
import io
import json
import logging
import re
import time
import zipfile
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import httpx
from sqlalchemy import delete

from app.core.ars import normalize_ars
from app.core.config import settings
from app.etl.common import (
    clear_indicator_values,
    get_or_create_indicator,
    normalize,
    upsert_region_indicator_value,
    with_session,
)
from app.models.region import Region
from app.models.indicator import IndicatorDefinition, RegionIndicatorValue
from sqlmodel import select

logger = logging.getLogger("etl.import_destatis")
logging.basicConfig(level=logging.INFO)


class GenesisRequestLimitError(RuntimeError):
    pass


@dataclass
class GenesisIndicatorSpec:
    key: str
    name: str
    category: str
    unit: str
    direction: str
    table_code: str
    source_name: str
    source_url: str
    methodology: str
    normalization_mode: str = "log"
    # optional explizite Spaltennamen im CSV (falls bekannt)
    ars_column: str | None = None
    value_column: str | None = None
    # optionale API-Parameter, z.B. content, region, etc.
    params: dict[str, str] | None = None
    parser_strategy: str = "generic"


# Beispielliste fuer einen vollen Destatis-Satz. Diese Liste kann/should ueber
# GENESIS_INDICATORS_JSON in .env projektindividuell ueberschrieben werden.
DEFAULT_INDICATOR_SPECS: list[GenesisIndicatorSpec] = [
    GenesisIndicatorSpec(
        key="population_total_destatis",
        name="Bevoelkerung gesamt",
        category="demographics",
        unit="count",
        direction="higher_is_better",
        table_code="12411-01-01-5",
        source_name="Regionaldatenbank Deutschland GENESIS",
        source_url="https://www.regionalstatistik.de/genesis/online",
        methodology="Gemeindebevoelkerung je AGS aus Regionalstatistik Tabelle 12411-01-01-5 (31.12., insgesamt).",
        normalization_mode="log",
        params={
            "regionalvariable": "GEMEIN",
            "classifyingvariable1": "GES",
            "classifyingkey1": "GESM,GESW",
            "language": "de",
        },
        parser_strategy="gemeinde_population_total",
    ),
    GenesisIndicatorSpec(
        key="female_share_destatis",
        name="Frauenanteil",
        category="demographics",
        unit="percent",
        direction="higher_is_better",
        table_code="12411-01-01-5",
        source_name="Regionaldatenbank Deutschland GENESIS",
        source_url="https://www.regionalstatistik.de/genesis/online",
        methodology="Frauenanteil je Gemeinde aus Regionalstatistik Tabelle 12411-01-01-5 (weiblich / insgesamt).",
        normalization_mode="linear",
        params={
            "regionalvariable": "GEMEIN",
            "classifyingvariable1": "GES",
            "classifyingkey1": "GESM,GESW",
            "language": "de",
        },
        parser_strategy="gemeinde_female_share",
    ),
    GenesisIndicatorSpec(
        key="youth_share_destatis",
        name="Anteil unter 18 Jahre",
        category="demographics",
        unit="percent",
        direction="higher_is_better",
        table_code="12411-02-03-5",
        source_name="Regionaldatenbank Deutschland GENESIS",
        source_url="https://www.regionalstatistik.de/genesis/online",
        methodology=(
            "Jugendanteil je Gemeinde aus Regionalstatistik Tabelle 12411-02-03-5 "
            "(unter 3 + 3-6 + 6-10 + 10-15 + 15-18) / insgesamt."
        ),
        normalization_mode="linear",
        params={
            "regionalvariable": "GEMEIN",
            "classifyingvariable1": "ALTX20",
            "classifyingkey1": "ALT000B03,ALT003B06,ALT006B10,ALT010B15,ALT015B18,ALT065B75,ALT075UM",
            "classifyingvariable2": "GES",
            "classifyingkey2": "GESM,GESW",
            "language": "de",
        },
        parser_strategy="gemeinde_age_share_u18",
    ),
    GenesisIndicatorSpec(
        key="senior_share_destatis",
        name="Anteil 65+ Jahre",
        category="demographics",
        unit="percent",
        direction="lower_is_better",
        table_code="12411-02-03-5",
        source_name="Regionaldatenbank Deutschland GENESIS",
        source_url="https://www.regionalstatistik.de/genesis/online",
        methodology="Seniorenanteil je Gemeinde aus Regionalstatistik Tabelle 12411-02-03-5 (65-75 + 75+) / insgesamt.",
        normalization_mode="linear",
        params={
            "regionalvariable": "GEMEIN",
            "classifyingvariable1": "ALTX20",
            "classifyingkey1": "ALT000B03,ALT003B06,ALT006B10,ALT010B15,ALT015B18,ALT065B75,ALT075UM",
            "classifyingvariable2": "GES",
            "classifyingkey2": "GESM,GESW",
            "language": "de",
        },
        parser_strategy="gemeinde_age_share_65plus",
    ),
]


def _credential_payload() -> dict[str, str] | None:
    # Backward compatibility: genesis_api_key kann als username/password identisch genutzt werden.
    username = (
        settings.genesis_username or settings.genesis_api_key or "").strip()
    password = (
        settings.genesis_password or settings.genesis_api_key or "").strip()
    if not username or not password:
        return None
    return {"username": username, "password": password}


def _credential_headers(auth: dict[str, str]) -> dict[str, str]:
    return {
        "username": auth["username"],
        "password": auth["password"],
        "user": auth["username"],
        "passwort": auth["password"],
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
    }


def _load_specs() -> list[GenesisIndicatorSpec]:
    if not settings.genesis_indicators_json:
        return DEFAULT_INDICATOR_SPECS

    raw = json.loads(settings.genesis_indicators_json)
    specs: list[GenesisIndicatorSpec] = []
    for item in raw:
        specs.append(
            GenesisIndicatorSpec(
                key=item["key"],
                name=item["name"],
                category=item.get("category", "demographics"),
                unit=item.get("unit", "value"),
                direction=item.get("direction", "higher_is_better"),
                table_code=item["table_code"],
                source_name=item.get("source_name", "Destatis GENESIS"),
                source_url=item.get(
                    "source_url", "https://www-genesis.destatis.de/datenbank/online#modal=web-service-api"
                ),
                methodology=item.get(
                    "methodology", "Regionalwert je Kreis aus GENESIS Tabelle."),
                normalization_mode=item.get("normalization_mode", "log"),
                ars_column=item.get("ars_column"),
                value_column=item.get("value_column"),
                params=item.get("params"),
                parser_strategy=item.get("parser_strategy", "generic"),
            )
        )
    return specs


def _genesis_base_url() -> str:
    marker = "/data/"
    if marker in settings.genesis_api_url:
        return settings.genesis_api_url.split(marker, 1)[0]
    return settings.genesis_api_url.rsplit("/", 1)[0]


def _requires_regionalstatistik(spec: GenesisIndicatorSpec) -> bool:
    return spec.parser_strategy.startswith("gemeinde_")


def _validate_endpoint_for_specs(specs: list[GenesisIndicatorSpec]) -> None:
    if not any(_requires_regionalstatistik(spec) for spec in specs):
        return

    host = (urlparse(settings.genesis_api_url).hostname or "").lower()
    if "regionalstatistik.de" in host:
        return

    raise RuntimeError(
        "Die konfigurierten Destatis-Indikatoren erwarten Gemeinde-Tabellen aus der Regionalstatistik, "
        f"aber GENESIS_API_URL zeigt auf {settings.genesis_api_url}. "
        "Setze GENESIS_API_URL=https://www.regionalstatistik.de/genesisws/rest/2020/data/table "
        "und verwende passende Regionalstatistik-Zugangsdaten."
    )


def _call_logincheck(auth: dict[str, str]) -> None:
    logincheck_url = f"{_genesis_base_url()}/helloworld/logincheck"
    params = {
        "username": auth["username"],
        "password": auth["password"],
    }
    headers = _credential_headers(auth)
    try:
        request = Request(
            f"{logincheck_url}?{urlencode(params)}", headers=headers, method="GET")
        with urlopen(request, timeout=settings.genesis_connect_timeout_seconds) as response:
            logger.info("GENESIS logincheck status=%s url=%s",
                        response.status, logincheck_url)
    except Exception as exc:
        logger.warning("GENESIS logincheck failed: %s", exc)


def _extract_error_detail(response: httpx.Response) -> tuple[str | None, str]:
    detail = response.text[:500]
    error_code: str | None = None
    try:
        data = response.json()
        error_code = str(data.get("Code") or data.get(
            "Status", {}).get("Code") or "")
        detail = (
            f"Code={data.get('Code') or data.get('Status', {}).get('Code')} "
            f"Type={data.get('Type') or data.get('Status', {}).get('Type')} "
            f"Content={data.get('Content') or data.get('Status', {}).get('Content')}"
        )
    except Exception:
        pass
    return error_code, detail


def _open_request(request: Request, timeout_seconds: float) -> tuple[int, dict[str, str], str]:
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            return response.status, dict(response.headers.items()), body
    except HTTPError as exc:
        body = exc.read()
        return exc.code, dict(exc.headers.items()), body


def _post_form(
    *,
    url: str,
    data: dict[str, str],
    headers: dict[str, str],
    timeout_seconds: float,
) -> httpx.Response:
    encoded = urlencode(data).encode("utf-8")
    request = Request(url, data=encoded, headers=headers, method="POST")
    status_code, response_headers, body = _open_request(
        request, timeout_seconds)
    return httpx.Response(status_code=status_code, headers=response_headers, content=body)


def _decode_zip_result(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("GENESIS Resultfile ist leer.")
        with archive.open(names[0]) as handle:
            return handle.read().decode("utf-8", errors="replace")


def _job_name_from_response(response: httpx.Response) -> str | None:
    try:
        data = response.json()
    except Exception:
        return None
    status = data.get("Status", {})
    content = status.get("Content") or ""
    match = re.search(r"abgerufen werden:\s*([A-Za-z0-9_-]+)", content)
    if match:
        return match.group(1)
    return None


def _list_jobs(auth: dict[str, str]) -> list[dict[str, str]]:
    headers = _credential_headers(auth)
    response = _post_form(
        url=f"{_genesis_base_url()}/catalogue/jobs",
        data={
            **auth,
            "sortcriterion": "time",
        },
        headers=headers,
        timeout_seconds=max(settings.genesis_connect_timeout_seconds, 60.0),
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"HTTP {response.status_code} beim Abruf der GENESIS-Jobliste.")
    data = response.json()
    if str(data.get("Status", {}).get("Code", "")) not in {"0", ""}:
        raise RuntimeError(
            f"GENESIS Jobliste fehlgeschlagen: {data.get('Status', {}).get('Content') or 'unbekannter Fehler'}"
        )
    jobs = data.get("List") or []
    return [job for job in jobs if isinstance(job, dict)]


def _download_resultfile(job_name: str, auth: dict[str, str]) -> str:
    headers = _credential_headers(auth)
    response = _post_form(
        url=f"{_genesis_base_url()}/data/resultfile",
        data={
            **auth,
            "name": job_name,
            "area": "all",
            "format": "ffcsv",
            "language": "de",
        },
        headers=headers,
        timeout_seconds=max(settings.genesis_read_timeout_seconds, 120.0),
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"HTTP {response.status_code} beim Abruf des GENESIS-Resultfiles {job_name}.")
    if "application/json" in (response.headers.get("content-type", "")):
        data = response.json()
        raise RuntimeError(
            f"GENESIS Resultfile {job_name} nicht verfuegbar: "
            f"{data.get('Status', {}).get('Content') or data.get('Content') or 'unbekannter Fehler'}"
        )
    return _decode_zip_result(response.content)


def _fetch_table_csv_via_job(spec: GenesisIndicatorSpec, auth: dict[str, str]) -> str:
    payload: dict[str, str] = {
        "name": spec.table_code,
        "area": "all",
        "format": "csv",
        "job": "true",
        **auth,
    }
    if spec.params:
        payload.update(spec.params)

    headers = _credential_headers(auth)
    job_url = settings.genesis_api_url.replace(
        "/data/table", "/data/tablefile")
    response = _post_form(
        url=job_url,
        data=payload,
        headers=headers,
        timeout_seconds=max(settings.genesis_read_timeout_seconds, 120.0),
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"HTTP {response.status_code} beim Start des GENESIS-Jobs fuer {spec.table_code}.")
    job_name = _job_name_from_response(response)
    if not job_name:
        raise RuntimeError(
            f"GENESIS-Jobname fuer Tabelle {spec.table_code} konnte nicht ermittelt werden.")

    max_polls = 36
    poll_interval_seconds = 10
    for _ in range(max_polls):
        jobs = _list_jobs(auth)
        for job in jobs:
            if job.get("Code") != job_name:
                continue
            state = (job.get("State") or "").strip().lower()
            if state == "fertig":
                return _download_resultfile(job_name, auth)
            if state in {"fehler", "abgebrochen"}:
                raise RuntimeError(
                    f"GENESIS-Job {job_name} fuer Tabelle {spec.table_code} endete mit Status {job.get('State')}.")
            break
        time.sleep(poll_interval_seconds)

    raise RuntimeError(
        f"GENESIS-Job {job_name} fuer Tabelle {spec.table_code} wurde nicht rechtzeitig fertig."
    )


def _fetch_table_csv(spec: GenesisIndicatorSpec, auth: dict[str, str]) -> str:
    payload: dict[str, str] = {
        "name": spec.table_code,
        "area": "all",
        "format": "csv",
        **auth,
    }
    if spec.params:
        payload.update(spec.params)

    payload_alt = {
        "name": spec.table_code,
        "area": "all",
        "format": "csv",
        "user": auth.get("username", ""),
        "passwort": auth.get("password", ""),
    }

    headers = _credential_headers(auth)

    last_exception: Exception | None = None
    max_attempts = max(settings.genesis_request_retries, 1)
    timeout_seconds = max(
        settings.genesis_connect_timeout_seconds,
        settings.genesis_read_timeout_seconds,
        settings.genesis_write_timeout_seconds,
        settings.genesis_pool_timeout_seconds,
    )

    for attempt in range(1, max_attempts + 1):
        try:
            response = _post_form(
                url=settings.genesis_api_url,
                data=payload,
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            logger.info("GENESIS POST status=%s table=%s url=%s",
                        response.status_code, spec.table_code, settings.genesis_api_url)
            if response.status_code == 401:
                response = _post_form(
                    url=settings.genesis_api_url,
                    data=payload_alt,
                    headers=headers,
                    timeout_seconds=timeout_seconds,
                )
                logger.info(
                    "GENESIS POST alt-auth status=%s table=%s url=%s",
                    response.status_code,
                    spec.table_code,
                    settings.genesis_api_url,
                )
        except TimeoutError as exc:
            last_exception = exc
            logger.warning(
                "GENESIS Timeout table=%s attempt=%s/%s api=%s",
                spec.table_code,
                attempt,
                max_attempts,
                settings.genesis_api_url,
            )
            if attempt == max_attempts:
                raise RuntimeError(
                    f"GENESIS timeout after {max_attempts} attempts "
                    f"(connect={settings.genesis_connect_timeout_seconds}s, "
                    f"read={settings.genesis_read_timeout_seconds}s)"
                ) from exc
            time.sleep(min(5 * attempt, 15))
            continue
        except URLError as exc:
            last_exception = exc
            if attempt == max_attempts:
                raise
            logger.warning(
                "GENESIS HTTP transport error table=%s attempt=%s/%s: %s",
                spec.table_code,
                attempt,
                max_attempts,
                exc,
            )
            time.sleep(min(5 * attempt, 15))
            continue

        error_code, detail = _extract_error_detail(response)

        if error_code == "6":
            logger.warning(
                "GENESIS request limit hit table=%s attempt=%s/%s: %s",
                spec.table_code,
                attempt,
                max_attempts,
                detail,
            )
            _call_logincheck(auth)
            if attempt == max_attempts:
                raise GenesisRequestLimitError(
                    f"GENESIS request limit persisted after {max_attempts} attempts - {detail}"
                )
            time.sleep(min(15 * attempt, 45))
            continue

        break
    else:
        if last_exception is not None:
            raise last_exception
        raise RuntimeError("GENESIS request failed without response")

    if response.status_code >= 400:
        _, detail = _extract_error_detail(response)
        raise RuntimeError(
            f"HTTP {response.status_code} bei GENESIS ({settings.genesis_api_url}) - {detail}"
        )

    # Bei API-Fehlern liefert GENESIS JSON mit Code/Type, nicht CSV.
    ctype = response.headers.get("content-type", "")
    text = response.text
    if "application/json" in ctype and text.strip().startswith("{"):
        data = response.json()
        if data.get("Type") == "ERROR":
            raise RuntimeError(
                f"GENESIS Fehler {data.get('Code')}: {data.get('Content')}")
        status = data.get("Status", {})
        if status.get("Code", 0) in (98, "98"):
            return _fetch_table_csv_via_job(spec, auth)
        if status.get("Code", 0) not in (0, "0"):
            raise RuntimeError(
                f"GENESIS Warnung {status.get('Code')}: {status.get('Content') or 'Keine Daten fuer die Selektion'}"
            )
        obj = data.get("Object") or {}
        content = obj.get("Content")
        if isinstance(content, str) and content.strip():
            return content
        raise RuntimeError(
            "GENESIS lieferte keine CSV-Inhalte fuer die angefragte Tabelle.")
    return text


def _to_float(value: str) -> float | None:
    value = value.strip().replace(".", "").replace(",", ".")
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _normalize_text(value: str) -> str:
    normalized = value.strip().lower()
    return (
        normalized.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


def _normalize_destatis_region_code(raw_code: str, region_type: str | None = None) -> str | None:
    code = normalize_ars(raw_code)
    if len(code) == 8:
        return code
    if len(code) == 5 and (region_type or "").strip().upper() == "KREISF":
        return f"{code}000"
    return None


def _iter_csv_rows(genesis_content: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(genesis_content), delimiter=";")
    return [[cell.strip() for cell in row] for row in reader]


def _parse_population_rows(content: str) -> list[tuple[str, dict[str, float]]]:
    parsed: list[tuple[str, dict[str, float]]] = []
    rows = _iter_csv_rows(content)
    if rows and rows[0] and rows[0][0].lstrip("\ufeff") == "statistics_code":
        grouped: dict[str, dict[str, float | None]] = {}
        for row in rows[1:]:
            if len(row) < 18 or not row[7].isdigit():
                continue
            ars = _normalize_destatis_region_code(row[7], row[5])
            if ars is None:
                continue
            value = _to_float(row[17])
            if value is None:
                continue
            gender_code = row[11]
            bucket = grouped.setdefault(
                ars, {"total": None, "male": None, "female": None})
            if gender_code == "GESM":
                bucket["male"] = value
            elif gender_code == "GESW":
                bucket["female"] = value
            elif gender_code == "":
                bucket["total"] = value
        return [
            (
                ars,
                {
                    "total": float(values["total"]),
                    "male": float(values["male"]),
                    "female": float(values["female"]),
                },
            )
            for ars, values in grouped.items()
            if values["total"] is not None and values["male"] is not None and values["female"] is not None
        ]

    for row in rows:
        if len(row) < 5 or not row[0].isdigit():
            continue
        ars = _normalize_destatis_region_code(
            row[0], "KREISF" if len(row[0]) == 5 else "GEMEIN")
        if ars is None:
            continue
        total = _to_float(row[2])
        male = _to_float(row[3])
        female = _to_float(row[4])
        if total is None or male is None or female is None:
            continue
        parsed.append(
            (
                ars,
                {
                    "total": total,
                    "male": male,
                    "female": female,
                },
            )
        )
    return parsed


def _parse_age_rows(content: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    rows = _iter_csv_rows(content)
    if rows and rows[0] and rows[0][0].lstrip("\ufeff") == "statistics_code":
        for row in rows[1:]:
            if len(row) < 18 or not row[7].isdigit():
                continue
            ars = _normalize_destatis_region_code(row[7], row[5])
            if ars is None:
                continue
            gender_code = row[11]
            if gender_code not in {"", None}:
                continue
            age_label = _normalize_text(row[16])
            total = _to_float(row[17])
            if total is None:
                continue
            bucket = grouped.setdefault(ars, {})
            bucket[age_label] = total
        return grouped

    for row in rows:
        if len(row) < 7 or not row[1].isdigit():
            continue
        ars = _normalize_destatis_region_code(
            row[1], "KREISF" if len(row[1]) == 5 else "GEMEIN")
        if ars is None:
            continue
        age_label = _normalize_text(row[3])
        total = _to_float(row[4])
        if total is None:
            continue
        bucket = grouped.setdefault(ars, {})
        bucket[age_label] = total
    return grouped


def _parse_genesis_content(spec: GenesisIndicatorSpec, content: str) -> list[tuple[str, float]]:
    if spec.parser_strategy in {"gemeinde_population_total", "gemeinde_female_share"}:
        parsed_rows = _parse_population_rows(content)
        if spec.parser_strategy == "gemeinde_population_total":
            return [(ars, values["total"]) for ars, values in parsed_rows if values["total"] > 0]
        return [
            (ars, (values["female"] / values["total"]) * 100.0)
            for ars, values in parsed_rows
            if values["total"] > 0
        ]

    if spec.parser_strategy in {"gemeinde_age_share_u18", "gemeinde_age_share_65plus"}:
        grouped = _parse_age_rows(content)
        youth_labels = {
            "unter 3 jahre",
            "3 bis unter 6 jahre",
            "6 bis unter 10 jahre",
            "10 bis unter 15 jahre",
            "15 bis unter 18 jahre",
        }
        senior_labels = {
            "65 bis unter 75 jahre",
            "75 jahre und mehr",
        }
        parsed: list[tuple[str, float]] = []
        for ars, values in grouped.items():
            total = values.get("insgesamt")
            if total is None or total <= 0:
                continue
            if spec.parser_strategy == "gemeinde_age_share_u18":
                share_base = sum(values.get(label, 0.0)
                                 for label in youth_labels)
            else:
                share_base = sum(values.get(label, 0.0)
                                 for label in senior_labels)
            parsed.append((ars, (share_base / total) * 100.0))
        return parsed

    return []


def _backfill_region_population(
    session,
    region_by_ars: dict[str, int],
    mapped: list[tuple[int, float]],
) -> int:
    values_by_region_id = {region_id: raw for region_id, raw in mapped}
    if not values_by_region_id:
        return 0

    updated = 0
    for region in session.exec(select(Region).where(Region.id.in_(list(values_by_region_id.keys())))):
        raw_value = values_by_region_id.get(region.id)
        if raw_value is None:
            continue
        population_value = int(round(raw_value))
        if region.population == population_value:
            continue
        region.population = population_value
        session.add(region)
        updated += 1
    if updated:
        session.commit()
    return updated


def main() -> None:
    logger.info("Destatis/GENESIS-Import gestartet")

    with with_session() as cleanup_session:
        for legacy_key in ["population_density", "population_young_ratio"]:
            legacy = cleanup_session.exec(
                select(IndicatorDefinition).where(
                    IndicatorDefinition.key == legacy_key)
            ).first()
            if legacy:
                cleanup_session.exec(
                    delete(RegionIndicatorValue).where(
                        RegionIndicatorValue.indicator_id == legacy.id,
                        RegionIndicatorValue.period == settings.default_score_period,
                    )
                )
                cleanup_session.exec(delete(IndicatorDefinition).where(
                    IndicatorDefinition.id == legacy.id))
                cleanup_session.commit()
                logger.info("Legacy-Indicator entfernt: %s", legacy_key)

    auth = _credential_payload()
    if auth is None:
        logger.warning(
            "Keine GENESIS Zugangsdaten gesetzt (GENESIS_USERNAME/GENESIS_PASSWORD oder GENESIS_API_KEY). "
            "Destatis-Import wird ohne Bootstrap uebersprungen."
        )
        return

    specs = _load_specs()
    if not specs:
        logger.warning(
            "Keine Destatis-Indikator-Spezifikation vorhanden. Kein Write.")
        return
    _validate_endpoint_for_specs(specs)

    with with_session() as session:
        regions = list(session.exec(select(Region)))
        region_by_ars = {region.ars: region.id for region in regions}
        content_cache: dict[tuple[str, tuple[tuple[str, str], ...]], str] = {}

        written = 0
        for spec in specs:
            try:
                cache_key = (
                    spec.table_code,
                    tuple(sorted((spec.params or {}).items())),
                )
                logger.info("Lade Destatis-Indikator %s aus Tabelle %s",
                            spec.key, spec.table_code)
                content = content_cache.get(cache_key)
                if content is None:
                    content = _fetch_table_csv(spec, auth)
                    content_cache[cache_key] = content
                rows = _parse_genesis_content(spec, content)
            except GenesisRequestLimitError as exc:
                logger.warning(
                    "Destatis-Tabelle %s (%s) fehlgeschlagen: %s", spec.table_code, spec.key, exc)
                cooldown_seconds = max(
                    settings.genesis_limit_cooldown_seconds, 0)
                if cooldown_seconds > 0:
                    logger.warning(
                        "GENESIS request limit aktiv. Warte %s Sekunden vor Abbruch des Imports.",
                        cooldown_seconds,
                    )
                    time.sleep(cooldown_seconds)
                logger.warning(
                    "Destatis-Import wegen aktivem GENESIS Request-Limit abgebrochen. "
                    "Warte ca. 15 Minuten oder setze GENESIS_LIMIT_COOLDOWN_SECONDS."
                )
                return
            except Exception as exc:
                logger.warning(
                    "Destatis-Tabelle %s (%s) fehlgeschlagen: %s", spec.table_code, spec.key, exc)
                continue

            indicator = get_or_create_indicator(
                session,
                key=spec.key,
                name=spec.name,
                category=spec.category,
                unit=spec.unit,
                direction=spec.direction,
                normalization_mode=spec.normalization_mode,
                source_name=spec.source_name,
                source_url=spec.source_url,
                methodology=spec.methodology,
            )

            mapped: list[tuple[int, float]] = []
            for ars, raw in rows:
                region_id = region_by_ars.get(ars)
                if region_id is not None:
                    mapped.append((region_id, raw))

            if not mapped:
                clear_indicator_values(
                    session,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                )
                logger.warning(
                    "Destatis-Tabelle %s (%s) ergab keine exakt auf Gemeinden mappbaren Werte. "
                    "Vorhandene Werte fuer den Zeitraum wurden entfernt.",
                    spec.table_code,
                    spec.key,
                )
                continue

            clear_indicator_values(
                session,
                indicator_id=indicator.id,
                period=settings.default_score_period,
            )

            raw_values = [value for _, value in mapped]
            normalized_values = normalize(raw_values, spec.direction, mode=spec.normalization_mode)

            for (region_id, raw), norm in zip(mapped, normalized_values):
                upsert_region_indicator_value(
                    session,
                    region_id=region_id,
                    indicator_id=indicator.id,
                    period=settings.default_score_period,
                    raw_value=round(raw, 4),
                    normalized_value=norm,
                    quality_flag="ok",
                )

            if spec.key == "population_total_destatis":
                updated_regions = _backfill_region_population(
                    session, region_by_ars, mapped)
                if updated_regions:
                    logger.info(
                        "Region.population aus Destatis-Fallback aktualisiert: %s Regionen",
                        updated_regions,
                    )

            written += 1
            logger.info(
                "Destatis-Indikator %s geladen (table=%s, rows=%s)",
                spec.key,
                spec.table_code,
                len(mapped),
            )

        if written == 0:
            logger.warning("Kein Destatis-Indikator erfolgreich geladen.")
        else:
            logger.info(
                "Destatis/GENESIS-Import abgeschlossen (%s Indikatoren)", written)


if __name__ == "__main__":
    main()

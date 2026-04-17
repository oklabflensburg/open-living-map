import re
import unicodedata


ARS_LENGTH = 12
AGS_LENGTH = 8
DISTRICT_CODE_LENGTH = 5


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def to_ags(value: str) -> str | None:
    digits = digits_only(value)
    if not digits:
        return None
    if len(digits) >= AGS_LENGTH:
        return digits[:AGS_LENGTH]
    if len(digits) == DISTRICT_CODE_LENGTH:
        return f"{digits}000"
    return digits.zfill(AGS_LENGTH)


def to_district_code(value: str) -> str | None:
    digits = digits_only(value)
    if not digits:
        return None
    if len(digits) >= DISTRICT_CODE_LENGTH:
        return digits[:DISTRICT_CODE_LENGTH]
    return digits.zfill(DISTRICT_CODE_LENGTH)


def normalize_ars(value: str) -> str:
    digits = digits_only(value)
    if not digits:
        return value

    # AGS-first Canonicalisierung: Gemeinden als 8-stelliger AGS.
    ags = to_ags(digits)
    if ags:
        return ags

    if len(digits) >= ARS_LENGTH:
        return digits[:ARS_LENGTH]
    return digits.zfill(ARS_LENGTH)


def lookup_candidates(value: str) -> list[str]:
    digits = digits_only(value)
    if not digits:
        return [value]

    candidates: set[str] = {digits}

    norm = normalize_ars(digits)
    if norm:
        candidates.add(norm)

    ags = to_ags(digits)
    if ags:
        candidates.add(ags)
        # legacy 12-stellige AGS-Form
        candidates.add(f"{ags}0000")

    district_code = to_district_code(digits)
    if district_code:
        candidates.add(district_code)
        # legacy 12-digit district form
        candidates.add(f"{district_code}0000000")

    return list(candidates)


def slugify_region_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "region"

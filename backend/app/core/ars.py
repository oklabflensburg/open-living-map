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


def slugify_region_name(
    name: str,
    district_name: str = "",
    state_name: str = "",
    remark: str = "",
    district_type: str = "",
) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    normalized_district = unicodedata.normalize("NFKD", district_name)
    normalized_district_type = unicodedata.normalize("NFKD", district_type)
    normalized_state = unicodedata.normalize("NFKD", state_name)

    def _simplified(value: str) -> str:
        ascii_value = value.encode("ascii", "ignore").decode("ascii").lower()
        return re.sub(r"[^a-z0-9]+", " ", ascii_value).strip()

    simplified_name = _simplified(normalized)
    simplified_district = _simplified(normalized_district)
    simplified_state = _simplified(normalized_state)

    if simplified_district and simplified_district in simplified_name:
        normalized_district = ""
        normalized_district_type = ""
    if simplified_state and simplified_state in simplified_name:
        normalized_state = ""
    if normalized_district_type and normalized_district.lower().startswith(
            normalized_district_type.lower()
    ):
        normalized_district_type = ""
    combined = (
        f"{normalized} {normalized_district_type} "
        f"{normalized_district} {normalized_state}"
    ).strip()

    if remark != '' and remark == "kreisfrei":
        combined = f"{normalized} {normalized_state}".strip()

    ascii_name = combined.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name.lower()).strip("-")

    return slug

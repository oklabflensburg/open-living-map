from app.schemas.recommendation import RecommendationInput

CATEGORY_LABELS = {
    "climate": "Klima",
    "air": "Luftqualität",
    "safety": "Verkehrssicherheit",
    "demographics": "Demografie/Familie",
    "amenities": "Alltagsnähe",
    "landuse": "Flächennutzung",
    "oepnv": "ÖPNV",
}


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} und {labels[1]}"
    return f"{', '.join(labels[:-1])} und {labels[-1]}"


def build_reason(category_scores: dict[str, float], preferences: RecommendationInput) -> str:
    weight_map = {
        "climate": preferences.climate_weight,
        "air": preferences.air_weight,
        "safety": preferences.safety_weight,
        "demographics": preferences.demographics_weight,
        "amenities": preferences.amenities_weight,
        "landuse": preferences.landuse_weight,
        "oepnv": preferences.oepnv_weight,
    }
    positive_weights = {key: weight for key, weight in weight_map.items() if weight > 0}
    if not positive_weights:
        return "Alle Gewichte waren 0, daher ergibt sich ein neutraler Gesamtscore von 0."

    highest_weight = max(positive_weights.values())
    emphasized_keys = [
        key for key, weight in positive_weights.items() if weight == highest_weight
    ]
    emphasized_labels = [CATEGORY_LABELS.get(key, key) for key in emphasized_keys]

    contribution_denominator = sum(positive_weights.values())
    contribution_map = {
        key: category_scores.get(key, 0.0) * weight / contribution_denominator
        for key, weight in positive_weights.items()
    }
    strongest_key = max(
        contribution_map,
        key=lambda key: (contribution_map[key], category_scores.get(key, 0.0), positive_weights[key]),
    )
    strongest_label = CATEGORY_LABELS.get(strongest_key, strongest_key)
    strongest_contribution = contribution_map[strongest_key]

    if len(emphasized_keys) == len(positive_weights):
        return (
            f"Dein Profil gewichtet alle Kategorien ähnlich; "
            f"den größten Beitrag liefert hier {strongest_label} "
            f"mit {strongest_contribution:.1f} Punkten."
        )

    return (
        f"Dein Profil gewichtet {_join_labels(emphasized_labels)} stark; "
        f"den größten Beitrag liefert hier {strongest_label} "
        f"mit {strongest_contribution:.1f} Punkten."
    )

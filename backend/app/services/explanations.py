from app.schemas.recommendation import RecommendationInput


def build_reason(category_scores: dict[str, float], preferences: RecommendationInput) -> str:
    weight_map = {
        "climate": preferences.climate_weight,
        "air": preferences.air_weight,
        "safety": preferences.safety_weight,
        "demographics": preferences.demographics_weight,
        "amenities": preferences.amenities_weight,
        "oepnv": preferences.oepnv_weight,
    }
    if sum(weight_map.values()) == 0:
        return "Alle Gewichte waren 0, daher ergibt sich ein neutraler Gesamtscore von 0."

    strongest = max(weight_map, key=weight_map.get)
    strongest_score = category_scores.get(strongest, 0)
    return f"Starker Treiber war {strongest} mit Teilscore {strongest_score:.1f}."

from types import SimpleNamespace

from app.schemas.recommendation import RecommendationInput
from app.services.scoring import ScoringService


def test_recommendation_input_accepts_hard_filters() -> None:
    payload = RecommendationInput(
        climate_weight=1,
        air_weight=2,
        safety_weight=3,
        demographics_weight=4,
        amenities_weight=5,
        landuse_weight=0,
        oepnv_weight=5,
        state_code="01",
        min_air_score=60,
        min_oepnv_score=75,
        coverage_min=50,
    )

    assert payload.state_code == "01"
    assert payload.preset is None
    assert payload.min_air_score == 60
    assert payload.min_oepnv_score == 75
    assert payload.coverage_min == 50


def test_recommendation_input_normalizes_nationwide_scope() -> None:
    payload = RecommendationInput(
        climate_weight=1,
        air_weight=1,
        safety_weight=1,
        demographics_weight=1,
        amenities_weight=1,
        landuse_weight=1,
        oepnv_weight=1,
        state_code="deutschlandweit",
    )

    assert payload.state_code is None


def test_weighted_total_penalizes_missing_coverage_for_weighted_categories() -> None:
    preferences = RecommendationInput(
        climate_weight=5,
        air_weight=5,
        safety_weight=0,
        demographics_weight=0,
        amenities_weight=0,
        landuse_weight=0,
        oepnv_weight=0,
    )

    score = ScoringService.weighted_total(
        {
            "climate": 20,
            "air": 80,
            "safety": 0,
            "demographics": 0,
            "amenities": 0,
            "landuse": 0,
            "oepnv": 0,
        },
        preferences,
        {
            "climate": 0,
            "air": 1,
            "safety": 0,
            "demographics": 0,
            "amenities": 0,
            "landuse": 0,
            "oepnv": 0,
        },
    )

    assert score == 40


def test_weighted_total_keeps_full_score_when_weighted_categories_have_coverage() -> None:
    preferences = RecommendationInput(
        climate_weight=5,
        air_weight=5,
        safety_weight=0,
        demographics_weight=0,
        amenities_weight=0,
        landuse_weight=0,
        oepnv_weight=0,
    )

    score = ScoringService.weighted_total(
        {
            "climate": 20,
            "air": 80,
            "safety": 0,
            "demographics": 0,
            "amenities": 0,
            "landuse": 0,
            "oepnv": 0,
        },
        preferences,
        {
            "climate": 1,
            "air": 1,
            "safety": 0,
            "demographics": 0,
            "amenities": 0,
            "landuse": 0,
            "oepnv": 0,
        },
    )

    assert score == 50


def test_urban_preset_blends_population_into_profile_score() -> None:
    preferences = RecommendationInput(
        preset="urban",
        climate_weight=0,
        air_weight=0,
        safety_weight=0,
        demographics_weight=0,
        amenities_weight=5,
        landuse_weight=0,
        oepnv_weight=5,
    )

    small_place_score = ScoringService.weighted_total(
        {
            "climate": 50,
            "air": 50,
            "safety": 50,
            "demographics": 50,
            "amenities": 50,
            "landuse": 50,
            "oepnv": 50,
        },
        preferences,
        {
            "climate": 1,
            "air": 1,
            "safety": 1,
            "demographics": 1,
            "amenities": 1,
            "landuse": 1,
            "oepnv": 1,
        },
        population=5_000,
    )
    large_city_score = ScoringService.weighted_total(
        {
            "climate": 50,
            "air": 50,
            "safety": 50,
            "demographics": 50,
            "amenities": 50,
            "landuse": 50,
            "oepnv": 50,
        },
        preferences,
        {
            "climate": 1,
            "air": 1,
            "safety": 1,
            "demographics": 1,
            "amenities": 1,
            "landuse": 1,
            "oepnv": 1,
        },
        population=250_000,
    )

    assert small_place_score == 40
    assert large_city_score == 60


def test_urban_preset_is_penalized_when_most_weighted_categories_are_missing() -> None:
    preferences = RecommendationInput(
        preset="urban",
        climate_weight=0,
        air_weight=0,
        safety_weight=0,
        demographics_weight=0,
        amenities_weight=5,
        landuse_weight=0,
        oepnv_weight=5,
    )

    score = ScoringService.weighted_total(
        {
            "climate": 0,
            "air": 88,
            "safety": 0,
            "demographics": 0,
            "amenities": 0,
            "landuse": 0,
            "oepnv": 0,
        },
        preferences,
        {
            "climate": 0,
            "air": 1,
            "safety": 0,
            "demographics": 0,
            "amenities": 0,
            "landuse": 0,
            "oepnv": 0,
        },
        population=250_000,
    )

    assert score < 10


def test_preset_weights_are_applied_in_backend() -> None:
    preferences = RecommendationInput(
        preset="air-climate",
        climate_weight=0,
        air_weight=0,
        safety_weight=0,
        demographics_weight=0,
        amenities_weight=0,
        landuse_weight=0,
        oepnv_weight=0,
    )

    normalized = ScoringService.apply_preset_weights(preferences)

    assert normalized.climate_weight == 5
    assert normalized.air_weight == 5
    assert normalized.safety_weight == 2
    assert normalized.demographics_weight == 1
    assert normalized.amenities_weight == 2
    assert normalized.landuse_weight == 3
    assert normalized.oepnv_weight == 2


def test_scoring_service_passes_hard_filters_to_repository() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def list_ranked_snapshots_by_preferences(self, **kwargs):
            self.calls.append(kwargs)
            return []

        def list_indicator_values_for_regions(self, region_ids):
            return {}

    service = ScoringService.__new__(ScoringService)
    fake_repository = FakeRepository()
    service.repository = fake_repository
    preferences = RecommendationInput(
        climate_weight=1,
        air_weight=1,
        safety_weight=1,
        demographics_weight=1,
        amenities_weight=1,
        landuse_weight=1,
        oepnv_weight=1,
        state_code="13",
        min_air_score=40,
        coverage_min=25,
    )

    response = service.get_recommendations(preferences)

    assert response.items == []
    assert fake_repository.calls[0]["state_code"] == "13"
    assert fake_repository.calls[0]["coverage_min"] == 25
    assert fake_repository.calls[0]["urbanity_boost"] is False
    assert fake_repository.calls[0]["min_scores"] == {
        "climate": None,
        "air": 40,
        "safety": None,
        "demographics": None,
        "amenities": None,
        "landuse": None,
        "oepnv": None,
    }


def test_scoring_service_passes_nationwide_scope_to_repository() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def list_ranked_snapshots_by_preferences(self, **kwargs):
            self.calls.append(kwargs)
            return []

        def list_indicator_values_for_regions(self, region_ids):
            return {}

    service = ScoringService.__new__(ScoringService)
    fake_repository = FakeRepository()
    service.repository = fake_repository
    preferences = RecommendationInput(
        climate_weight=3,
        air_weight=3,
        safety_weight=4,
        demographics_weight=5,
        amenities_weight=5,
        landuse_weight=3,
        oepnv_weight=3,
        state_code="DE",
    )

    response = service.get_recommendations(preferences)

    assert response.items == []
    assert fake_repository.calls[0]["state_code"] is None


def test_nationwide_results_are_selected_from_multiple_states() -> None:
    rows = [
        (SimpleNamespace(state_code="08"), SimpleNamespace()),
        (SimpleNamespace(state_code="08"), SimpleNamespace()),
        (SimpleNamespace(state_code="08"), SimpleNamespace()),
        (SimpleNamespace(state_code="08"), SimpleNamespace()),
        (SimpleNamespace(state_code="09"), SimpleNamespace()),
        (SimpleNamespace(state_code="06"), SimpleNamespace()),
        (SimpleNamespace(state_code="05"), SimpleNamespace()),
    ]

    selected = ScoringService._select_nationwide_rows(rows, limit=5)

    assert [row[0].state_code for row in selected] == ["08", "08", "09", "06", "05"]


def test_scoring_service_fetches_larger_candidate_pool_for_nationwide_results() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def list_ranked_snapshots_by_preferences(self, **kwargs):
            self.calls.append(kwargs)
            return []

        def list_indicator_values_for_regions(self, region_ids):
            return {}

    service = ScoringService.__new__(ScoringService)
    fake_repository = FakeRepository()
    service.repository = fake_repository
    preferences = RecommendationInput(
        climate_weight=3,
        air_weight=3,
        safety_weight=4,
        demographics_weight=5,
        amenities_weight=5,
        landuse_weight=3,
        oepnv_weight=3,
        state_code=None,
    )

    response = service.get_recommendations(preferences, limit=10)

    assert response.items == []
    assert fake_repository.calls[0]["limit"] == 100


def test_scoring_service_passes_backend_preset_weights_to_repository() -> None:
    class FakeRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def list_ranked_snapshots_by_preferences(self, **kwargs):
            self.calls.append(kwargs)
            return []

        def list_indicator_values_for_regions(self, region_ids):
            return {}

    service = ScoringService.__new__(ScoringService)
    fake_repository = FakeRepository()
    service.repository = fake_repository
    preferences = RecommendationInput(
        preset="transit",
        climate_weight=0,
        air_weight=0,
        safety_weight=0,
        demographics_weight=0,
        amenities_weight=0,
        landuse_weight=0,
        oepnv_weight=0,
    )

    response = service.get_recommendations(preferences)

    assert response.items == []
    assert fake_repository.calls[0]["weights"] == {
        "climate": 2,
        "air": 3,
        "safety": 3,
        "demographics": 1,
        "amenities": 4,
        "landuse": 2,
        "oepnv": 5,
    }

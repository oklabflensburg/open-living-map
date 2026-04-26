from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str
    env: str
    api_prefix: str
    cors_allow_origins: str
    database_url: str
    default_score_period: str
    raw_data_dir: str
    staging_data_dir: str
    genesis_api_key: str | None
    genesis_username: str | None
    genesis_password: str | None
    genesis_indicators_json: str | None
    genesis_api_url: str
    genesis_connect_timeout_seconds: float
    genesis_read_timeout_seconds: float
    genesis_write_timeout_seconds: float
    genesis_pool_timeout_seconds: float
    genesis_request_retries: int
    genesis_limit_cooldown_seconds: int
    uba_api_base: str
    dwd_base_url: str
    dwd_max_stations: int
    dwd_recent_cache_max_age_hours: int
    geofabrik_germany_pbf_url: str
    bkg_district_table: str
    bkg_municipality_table: str
    bkg_geometry_column: str
    bkg_geometry_flavour: int
    oepnv_gtfs_urls: str | None
    oepnv_http_username: str | None
    oepnv_http_password: str | None
    wikidata_sparql_url: str
    wikipedia_language: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def raw_data_path(self) -> Path:
        return (REPO_ROOT / self.raw_data_dir).resolve()

    @property
    def staging_data_path(self) -> Path:
        return (REPO_ROOT / self.staging_data_dir).resolve()

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()

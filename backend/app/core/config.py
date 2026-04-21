from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Wohnort-Kompass API"
    env: str = "development"
    api_prefix: str = "/api/v1"
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    database_url: str = "postgresql+psycopg://wohnortkompass:wohnortkompass@localhost:5433/wohnortkompass"
    default_score_period: str = "current"
    raw_data_dir: str = "../../data/raw"
    staging_data_dir: str = "../../data/staging"
    genesis_api_key: str | None = None
    genesis_username: str | None = None
    genesis_password: str | None = None
    genesis_indicators_json: str | None = None
    genesis_api_url: str = "https://www.regionalstatistik.de/genesisws/rest/2020/data/table"
    genesis_connect_timeout_seconds: float = 30.0
    genesis_read_timeout_seconds: float = 600.0
    genesis_write_timeout_seconds: float = 60.0
    genesis_pool_timeout_seconds: float = 60.0
    genesis_request_retries: int = 3
    genesis_limit_cooldown_seconds: int = 0
    uba_api_base: str = "https://www.umweltbundesamt.de/api/air-data/v4"
    dwd_base_url: str = (
        "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl"
    )
    dwd_max_stations: int = 0
    dwd_recent_cache_max_age_hours: int = 12
    geofabrik_germany_pbf_url: str = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"
    bkg_district_table: str = "public.vg25_krs"
    bkg_municipality_table: str = "public.vg25_gem"
    bkg_geometry_column: str = "geom"
    bkg_geometry_flavour: int = 4
    oepnv_gtfs_urls: str | None = (
        "https://www.opendata-oepnv.de/fileadmin/datasets/delfi/20260413_fahrplaene_gesamtdeutschland_gtfs.zip"
    )
    oepnv_http_username: str | None = None
    oepnv_http_password: str | None = None
    wikidata_sparql_url: str = "https://query.wikidata.org/sparql"
    wikipedia_language: str = "de"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def raw_data_path(self) -> Path:
        return (Path(__file__).resolve().parents[3] / self.raw_data_dir).resolve()

    @property
    def staging_data_path(self) -> Path:
        return (Path(__file__).resolve().parents[3] / self.staging_data_dir).resolve()

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()

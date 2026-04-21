export interface Region {
  ars: string
  slug: string
  name: string
  level: string
  state_code: string
  state_name: string
  district_name: string | null
  population: number | null
  area_km2: number | null
  centroid_lat: number | null
  centroid_lon: number | null
  wikidata_id: string | null
  wikidata_url: string | null
  wikipedia_url: string | null
}

export interface RegionListResponse {
  items: Region[]
}

export interface RecommendationInput {
  climate_weight: number
  air_weight: number
  safety_weight: number
  demographics_weight: number
  amenities_weight: number
  landuse_weight: number
  oepnv_weight: number
  state_code: string | null
}

export interface RecommendationItem {
  ars: string
  slug: string
  name: string
  level: string
  state_name: string
  district_name: string | null
  centroid_lat: number | null
  centroid_lon: number | null
  score_total: number
  score_profile: number
  score_climate: number
  score_air: number
  score_safety: number
  score_demographics: number
  score_amenities: number
  score_landuse: number
  score_oepnv: number
  coverage_climate: number
  coverage_air: number
  coverage_safety: number
  coverage_demographics: number
  coverage_amenities: number
  coverage_landuse: number
  coverage_oepnv: number
  trust_updated_at: string | null
  trust_sources: string[]
  trust_quality_notes: string[]
  reason: string
  score_formula: string
  calculation_details: string[]
  indicators: RecommendationIndicatorDetail[]
}

export interface RecommendationResponse {
  items: RecommendationItem[]
}

export interface RecommendationIndicatorDetail {
  key: string
  name: string
  category: string
  unit: string
  raw_value: number
  normalized_value: number
  quality_flag: string
  source_name: string
  updated_at: string | null
  text: string
}

export interface AmenityStat {
  category: string
  label: string
  count_total: number
  per_10k: number
}

export interface AccidentStat {
  category: string
  label: string
  count_total: number
}

export interface AirStationInfo {
  indicator_key: string
  label: string
  raw_value: number | null
  station_id: string
  station_code: string | null
  station_name: string
  latitude: number | null
  longitude: number | null
  station_page_url: string | null
  measures_url: string
}

export interface ClimateStationInfo {
  indicator_key: string
  label: string
  raw_value: number | null
  station_id: string
  station_name: string
  latitude: number | null
  longitude: number | null
  source_url: string | null
}

export interface LandUseStat {
  year: number
  forest_share_pct: number | null
  settlement_transport_share_pct: number | null
  agriculture_share_pct: number | null
  transport_share_pct: number | null
  settlement_transport_sqm_per_capita: number | null
}

export interface ScoreCoverage {
  climate: number
  air: number
  safety: number
  demographics: number
  amenities: number
  landuse: number
  oepnv: number
}

export interface CategoryFreshness {
  updated_at: string | null
  sources: string[]
}

export interface ScoreFreshness {
  climate: CategoryFreshness
  air: CategoryFreshness
  safety: CategoryFreshness
  demographics: CategoryFreshness
  amenities: CategoryFreshness
  landuse: CategoryFreshness
  oepnv: CategoryFreshness
}

export interface CategoryQualitySummary {
  status: string
  notes: string[]
}

export interface ScoreQualitySummary {
  climate: CategoryQualitySummary
  air: CategoryQualitySummary
  safety: CategoryQualitySummary
  demographics: CategoryQualitySummary
  amenities: CategoryQualitySummary
  landuse: CategoryQualitySummary
  oepnv: CategoryQualitySummary
}

export interface GeoJsonFeatureCollection {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    geometry: Record<string, unknown>
    properties: Record<string, unknown>
  }>
}

export interface RegionDetailResponse {
  region: Region
  scores: Record<string, number>
  coverage: ScoreCoverage
  freshness: ScoreFreshness
  quality: ScoreQualitySummary
  highlights: string[]
  source_links: string[]
  amenity_stats: AmenityStat[]
  accident_stats: AccidentStat[]
  air_stations: AirStationInfo[]
  climate_stations: ClimateStationInfo[]
  land_use_stat: LandUseStat | null
  geometry: Record<string, unknown> | null
  score_formula: string
  calculation_details: string[]
  indicators: RecommendationIndicatorDetail[]
}

export interface IndicatorMetadata {
  key: string
  name: string
  category: string
  unit: string
  direction: string
  normalization_mode: string
  source_name: string
  source_url: string
  methodology: string
}

export interface IndicatorMetadataResponse {
  items: IndicatorMetadata[]
}

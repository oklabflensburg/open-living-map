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

export interface LandUseStat {
  year: number
  forest_share_pct: number | null
  settlement_transport_share_pct: number | null
  agriculture_share_pct: number | null
  transport_share_pct: number | null
  settlement_transport_sqm_per_capita: number | null
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
  highlights: string[]
  source_links: string[]
  amenity_stats: AmenityStat[]
  accident_stats: AccidentStat[]
  air_stations: AirStationInfo[]
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

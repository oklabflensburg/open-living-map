import type { RecommendationInput } from '~/types/api'
import { finderPresetMap, type FinderPresetKey } from '~/utils/finderPresets'
import { recommendationCategories, type MinScoreKey } from '~/utils/recommendationConfig'

const WEIGHT_KEYS = [
  'climate_weight',
  'air_weight',
  'safety_weight',
  'demographics_weight',
  'amenities_weight',
  'landuse_weight',
  'oepnv_weight'
] as const

type WeightKey = typeof WEIGHT_KEYS[number]

const MIN_SCORE_KEYS = [
  'min_climate_score',
  'min_air_score',
  'min_safety_score',
  'min_demographics_score',
  'min_amenities_score',
  'min_landuse_score',
  'min_oepnv_score'
] as const

type NumericFilterKey = typeof MIN_SCORE_KEYS[number] | 'coverage_min'

const QUERY_KEY_BY_WEIGHT: Record<WeightKey, string> = {
  climate_weight: 'climate',
  air_weight: 'air',
  safety_weight: 'safety',
  demographics_weight: 'demographics',
  amenities_weight: 'amenities',
  landuse_weight: 'landuse',
  oepnv_weight: 'oepnv'
}

const QUERY_KEY_BY_FILTER: Record<NumericFilterKey, string> = {
  min_climate_score: 'minClimate',
  min_air_score: 'minAir',
  min_safety_score: 'minSafety',
  min_demographics_score: 'minDemographics',
  min_amenities_score: 'minAmenities',
  min_landuse_score: 'minLanduse',
  min_oepnv_score: 'minOepnv',
  coverage_min: 'coverage'
}

export type FinderPreferences = RecommendationInput & {
  preset: FinderPresetKey | null
}

export const DEFAULT_PREFERENCES: RecommendationInput = {
  climate_weight: 5,
  air_weight: 4,
  safety_weight: 3,
  demographics_weight: 4,
  amenities_weight: 5,
  landuse_weight: 3,
  oepnv_weight: 4,
  state_code: null,
  min_climate_score: null,
  min_air_score: null,
  min_safety_score: null,
  min_demographics_score: null,
  min_amenities_score: null,
  min_landuse_score: null,
  min_oepnv_score: null,
  coverage_min: null
}

export const DEFAULT_FINDER_PREFERENCES: FinderPreferences = {
  ...DEFAULT_PREFERENCES,
  preset: null
}

function firstQueryValue(value: unknown): string | null {
  if (Array.isArray(value)) {
    return typeof value[0] === 'string' ? value[0] : null
  }

  return typeof value === 'string' ? value : null
}

function clampWeight(value: string | null, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return fallback
  }

  return Math.min(5, Math.max(0, Math.round(parsed)))
}

function clampNullableScore(value: string | null): number | null {
  if (value === null || value.trim() === '') {
    return null
  }

  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return null
  }

  return Math.min(100, Math.max(0, Math.round(parsed)))
}

function parsePresetKey(value: string | null): FinderPresetKey | null {
  if (!value || !(value in finderPresetMap)) {
    return null
  }
  return value as FinderPresetKey
}

export function parsePreferenceQuery(
  query: Record<string, unknown>,
  fallback: FinderPreferences | RecommendationInput = DEFAULT_FINDER_PREFERENCES
): FinderPreferences {
  const preset = parsePresetKey(firstQueryValue(query.preset))
  const presetWeights = preset ? finderPresetMap[preset].weights : null
  const parsed: FinderPreferences = {
    ...fallback,
    ...(presetWeights || {}),
    state_code: fallback.state_code,
    preset
  }

  for (const key of WEIGHT_KEYS) {
    parsed[key] = clampWeight(firstQueryValue(query[QUERY_KEY_BY_WEIGHT[key]]), parsed[key])
  }

  if (presetWeights) {
    const stillMatchesPreset = Object.entries(presetWeights).every(
      ([key, value]) => parsed[key as WeightKey] === value
    )
    if (!stillMatchesPreset) {
      parsed.preset = null
    }
  }

  for (const key of MIN_SCORE_KEYS) {
    parsed[key] = clampNullableScore(firstQueryValue(query[QUERY_KEY_BY_FILTER[key]]))
  }

  parsed.coverage_min = clampNullableScore(firstQueryValue(query.coverage))
  const rawStateCode = firstQueryValue(query.state)
  parsed.state_code = rawStateCode && rawStateCode.trim() ? rawStateCode.trim() : null

  return parsed
}

export function buildPreferenceQuery(input: FinderPreferences | RecommendationInput): Record<string, string> {
  const query: Record<string, string> = {}

  for (const key of WEIGHT_KEYS) {
    query[QUERY_KEY_BY_WEIGHT[key]] = String(input[key])
  }

  if (input.state_code) {
    query.state = input.state_code
  }

  for (const key of MIN_SCORE_KEYS) {
    const value = input[key]
    if (value !== null) {
      query[QUERY_KEY_BY_FILTER[key]] = String(value)
    }
  }

  if (input.coverage_min !== null) {
    query.coverage = String(input.coverage_min)
  }

  if ('preset' in input && input.preset) {
    query.preset = input.preset
  }

  return query
}

export function buildRecommendationPayload(input: FinderPreferences | RecommendationInput): RecommendationInput {
  return {
    preset: 'preset' in input ? input.preset : null,
    climate_weight: input.climate_weight,
    air_weight: input.air_weight,
    safety_weight: input.safety_weight,
    demographics_weight: input.demographics_weight,
    amenities_weight: input.amenities_weight,
    landuse_weight: input.landuse_weight,
    oepnv_weight: input.oepnv_weight,
    state_code: input.state_code,
    min_climate_score: input.min_climate_score,
    min_air_score: input.min_air_score,
    min_safety_score: input.min_safety_score,
    min_demographics_score: input.min_demographics_score,
    min_amenities_score: input.min_amenities_score,
    min_landuse_score: input.min_landuse_score,
    min_oepnv_score: input.min_oepnv_score,
    coverage_min: input.coverage_min
  }
}

export function activeFilterTags(input: FinderPreferences | RecommendationInput, stateName: string): string[] {
  const tags: string[] = []

  if (input.state_code) {
    tags.push(`Bundesland: ${stateName}`)
  }

  if (input.coverage_min !== null) {
    tags.push(`Abdeckung mind. ${input.coverage_min} %`)
  }

  for (const category of recommendationCategories) {
    const minScore = input[category.minScoreKey as MinScoreKey]
    if (minScore !== null) {
      tags.push(`${category.label} mind. ${minScore}`)
    }
  }

  return tags
}

export function preferenceQueryEquals(
  query: Record<string, unknown>,
  input: FinderPreferences | RecommendationInput
): boolean {
  const expected = buildPreferenceQuery(input)
  const normalizedQuery = Object.fromEntries(
    Object.entries(query)
      .map(([key, value]) => [key, firstQueryValue(value)])
      .filter(([, value]) => value !== null)
  )

  const queryKeys = Object.keys(normalizedQuery).sort()
  const expectedKeys = Object.keys(expected).sort()

  if (queryKeys.length !== expectedKeys.length) {
    return false
  }

  return expectedKeys.every((key) => normalizedQuery[key] === expected[key])
}

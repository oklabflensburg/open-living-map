import type { RecommendationInput } from '~/types/api'

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

const QUERY_KEY_BY_WEIGHT: Record<WeightKey, string> = {
  climate_weight: 'climate',
  air_weight: 'air',
  safety_weight: 'safety',
  demographics_weight: 'demographics',
  amenities_weight: 'amenities',
  landuse_weight: 'landuse',
  oepnv_weight: 'oepnv'
}

export const DEFAULT_PREFERENCES: RecommendationInput = {
  climate_weight: 5,
  air_weight: 4,
  safety_weight: 3,
  demographics_weight: 4,
  amenities_weight: 5,
  landuse_weight: 3,
  oepnv_weight: 4,
  state_code: null
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

export function parsePreferenceQuery(
  query: Record<string, unknown>,
  fallback: RecommendationInput = DEFAULT_PREFERENCES
): RecommendationInput {
  const parsed: RecommendationInput = {
    ...fallback,
    state_code: fallback.state_code
  }

  for (const key of WEIGHT_KEYS) {
    parsed[key] = clampWeight(firstQueryValue(query[QUERY_KEY_BY_WEIGHT[key]]), fallback[key])
  }

  const rawStateCode = firstQueryValue(query.state)
  parsed.state_code = rawStateCode && rawStateCode.trim() ? rawStateCode.trim() : null

  return parsed
}

export function buildPreferenceQuery(input: RecommendationInput): Record<string, string> {
  const query: Record<string, string> = {}

  for (const key of WEIGHT_KEYS) {
    query[QUERY_KEY_BY_WEIGHT[key]] = String(input[key])
  }

  if (input.state_code) {
    query.state = input.state_code
  }

  return query
}

export function preferenceQueryEquals(query: Record<string, unknown>, input: RecommendationInput): boolean {
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

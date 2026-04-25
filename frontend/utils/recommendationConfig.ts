import type { RecommendationInput, RecommendationItem } from '~/types/api'

export type RecommendationCategory =
  | 'climate'
  | 'air'
  | 'safety'
  | 'demographics'
  | 'amenities'
  | 'landuse'
  | 'oepnv'

export type WeightKey =
  | 'climate_weight'
  | 'air_weight'
  | 'safety_weight'
  | 'demographics_weight'
  | 'amenities_weight'
  | 'landuse_weight'
  | 'oepnv_weight'

export type MinScoreKey =
  | 'min_climate_score'
  | 'min_air_score'
  | 'min_safety_score'
  | 'min_demographics_score'
  | 'min_amenities_score'
  | 'min_landuse_score'
  | 'min_oepnv_score'

export const recommendationCategories: Array<{
  key: RecommendationCategory
  weightKey: WeightKey
  minScoreKey: MinScoreKey
  shortQueryKey: string
  minScoreQueryKey: string
  label: string
  description: string
  color: string
  cardClass: string
  badgeClass: string
  barClass: string
}> = [
  {
    key: 'climate',
    weightKey: 'climate_weight',
    minScoreKey: 'min_climate_score',
    shortQueryKey: 'climate',
    minScoreQueryKey: 'minClimate',
    label: 'Klima',
    description: 'Klimatische Belastung und Niederschlag.',
    color: '#d97706',
    cardClass: 'border-amber-200 bg-amber-50/70',
    badgeClass: 'bg-amber-100 text-amber-800',
    barClass: 'bg-amber-600'
  },
  {
    key: 'air',
    weightKey: 'air_weight',
    minScoreKey: 'min_air_score',
    shortQueryKey: 'air',
    minScoreQueryKey: 'minAir',
    label: 'Luftqualität',
    description: 'Luftschadstoffe und Feinstaub.',
    color: '#0284c7',
    cardClass: 'border-sky-200 bg-sky-50/70',
    badgeClass: 'bg-sky-100 text-sky-800',
    barClass: 'bg-sky-600'
  },
  {
    key: 'safety',
    weightKey: 'safety_weight',
    minScoreKey: 'min_safety_score',
    shortQueryKey: 'safety',
    minScoreQueryKey: 'minSafety',
    label: 'Verkehrssicherheit',
    description: 'Unfallbelastung und Sicherheit im Straßenraum.',
    color: '#e11d48',
    cardClass: 'border-rose-200 bg-rose-50/70',
    badgeClass: 'bg-rose-100 text-rose-800',
    barClass: 'bg-rose-600'
  },
  {
    key: 'demographics',
    weightKey: 'demographics_weight',
    minScoreKey: 'min_demographics_score',
    shortQueryKey: 'demographics',
    minScoreQueryKey: 'minDemographics',
    label: 'Demografie/Familie',
    description: 'Bevölkerungsstruktur und Familienkontext.',
    color: '#7c3aed',
    cardClass: 'border-violet-200 bg-violet-50/70',
    badgeClass: 'bg-violet-100 text-violet-800',
    barClass: 'bg-violet-600'
  },
  {
    key: 'amenities',
    weightKey: 'amenities_weight',
    minScoreKey: 'min_amenities_score',
    shortQueryKey: 'amenities',
    minScoreQueryKey: 'minAmenities',
    label: 'Alltagsnähe',
    description: 'POIs und Versorgung im Alltag.',
    color: '#059669',
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    badgeClass: 'bg-emerald-100 text-emerald-800',
    barClass: 'bg-emerald-600'
  },
  {
    key: 'landuse',
    weightKey: 'landuse_weight',
    minScoreKey: 'min_landuse_score',
    shortQueryKey: 'landuse',
    minScoreQueryKey: 'minLanduse',
    label: 'Flächennutzung',
    description: 'Wald, Landwirtschaft und Siedlungsdruck.',
    color: '#b45309',
    cardClass: 'border-orange-200 bg-orange-50/70',
    badgeClass: 'bg-orange-100 text-orange-800',
    barClass: 'bg-orange-600'
  },
  {
    key: 'oepnv',
    weightKey: 'oepnv_weight',
    minScoreKey: 'min_oepnv_score',
    shortQueryKey: 'oepnv',
    minScoreQueryKey: 'minOepnv',
    label: 'ÖPNV',
    description: 'Haltestellen, Abfahrten und Angebotsdichte.',
    color: '#4f46e5',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    badgeClass: 'bg-indigo-100 text-indigo-800',
    barClass: 'bg-indigo-600'
  }
]

export const recommendationCategoryMap = Object.fromEntries(
  recommendationCategories.map((category) => [category.key, category])
) as Record<RecommendationCategory, (typeof recommendationCategories)[number]>

export function getCategoryScore(item: RecommendationItem, category: RecommendationCategory) {
  switch (category) {
    case 'climate':
      return item.score_climate
    case 'air':
      return item.score_air
    case 'safety':
      return item.score_safety
    case 'demographics':
      return item.score_demographics
    case 'amenities':
      return item.score_amenities
    case 'landuse':
      return item.score_landuse
    case 'oepnv':
      return item.score_oepnv
  }
}

export function getCategoryCoverage(item: RecommendationItem, category: RecommendationCategory) {
  switch (category) {
    case 'climate':
      return item.coverage_climate
    case 'air':
      return item.coverage_air
    case 'safety':
      return item.coverage_safety
    case 'demographics':
      return item.coverage_demographics
    case 'amenities':
      return item.coverage_amenities
    case 'landuse':
      return item.coverage_landuse
    case 'oepnv':
      return item.coverage_oepnv
  }
}

export function getCategoryWeight(input: RecommendationInput, category: RecommendationCategory) {
  return input[recommendationCategoryMap[category].weightKey]
}

export function getCategoryMinScore(input: RecommendationInput, category: RecommendationCategory) {
  return input[recommendationCategoryMap[category].minScoreKey]
}

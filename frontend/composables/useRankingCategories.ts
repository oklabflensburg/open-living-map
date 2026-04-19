import type { RecommendationItem } from '~/types/api'

export type RankingCategory = 'climate' | 'air' | 'safety' | 'demographics' | 'amenities' | 'landuse' | 'oepnv'

type RankingCategoryMeta = {
  key: RankingCategory
  label: string
  description: string
  cardClass: string
  badgeClass: string
}

export const rankingCategories: RankingCategoryMeta[] = [
  {
    key: 'climate',
    label: 'Klima',
    description: 'Top 100 nach Klima-Score aus DWD- und Flächenatlas-Daten.',
    cardClass: 'border-amber-200 bg-amber-50/70',
    badgeClass: 'bg-amber-100 text-amber-800'
  },
  {
    key: 'air',
    label: 'Luftqualität',
    description: 'Top 100 nach Luftqualitäts-Score.',
    cardClass: 'border-sky-200 bg-sky-50/70',
    badgeClass: 'bg-sky-100 text-sky-800'
  },
  {
    key: 'safety',
    label: 'Verkehrssicherheit',
    description: 'Top 100 nach Sicherheits-Score.',
    cardClass: 'border-rose-200 bg-rose-50/70',
    badgeClass: 'bg-rose-100 text-rose-800'
  },
  {
    key: 'demographics',
    label: 'Demografie/Familie',
    description: 'Top 100 nach Demografie-Score.',
    cardClass: 'border-violet-200 bg-violet-50/70',
    badgeClass: 'bg-violet-100 text-violet-800'
  },
  {
    key: 'amenities',
    label: 'Alltagsnähe',
    description: 'Top 100 nach Alltagsnähe-Score.',
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    badgeClass: 'bg-emerald-100 text-emerald-800'
  },
  {
    key: 'landuse',
    label: 'Flächennutzung',
    description: 'Top 100 nach Flächennutzungs-Score aus Flächenatlas-Daten.',
    cardClass: 'border-orange-200 bg-orange-50/70',
    badgeClass: 'bg-orange-100 text-orange-800'
  },
  {
    key: 'oepnv',
    label: 'ÖPNV',
    description: 'Top 100 nach ÖPNV-Score.',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    badgeClass: 'bg-indigo-100 text-indigo-800'
  }
]

export function getRankingCategory(category: string) {
  return rankingCategories.find((item) => item.key === category)
}

export function getRankingScore(item: RecommendationItem, category: RankingCategory) {
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

export function buildTopRankingPath(stateSlug: string, category: RankingCategory) {
  return `/top-100/${stateSlug}/${category}`
}

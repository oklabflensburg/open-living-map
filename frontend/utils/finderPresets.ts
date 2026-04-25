import type { RecommendationInput } from '~/types/api'
import type { WeightKey } from '~/utils/recommendationConfig'

export type FinderPresetKey = 'family' | 'transit' | 'air-climate' | 'urban' | 'quiet-nature'

export type FinderPresetDefinition = {
  key: FinderPresetKey
  label: string
  description: string
  accentLabel: string
  theme: {
    cardClass: string
    activeClass: string
    badgeClass: string
    dotClass: string
  }
  weights: Pick<RecommendationInput, WeightKey>
}

export const finderPresets: FinderPresetDefinition[] = [
  {
    key: 'family',
    label: 'Familienfreundlich',
    description: 'Stärkerer Fokus auf Alltag, Demografie, Sicherheit und solide Mobilität.',
    accentLabel: 'Alltag + Sicherheit',
    theme: {
      cardClass: 'border-violet-200 bg-violet-50/60 hover:border-violet-300 hover:bg-violet-50',
      activeClass: 'border-violet-500 bg-violet-100 shadow-sm ring-2 ring-violet-100',
      badgeClass: 'bg-violet-100 text-violet-800',
      dotClass: 'bg-violet-500'
    },
    weights: {
      climate_weight: 3,
      air_weight: 3,
      safety_weight: 4,
      demographics_weight: 5,
      amenities_weight: 5,
      landuse_weight: 3,
      oepnv_weight: 3
    }
  },
  {
    key: 'transit',
    label: 'Autofrei / ÖPNV-stark',
    description: 'Priorisiert ÖPNV und Alltagsnähe, ohne Luft und Sicherheit auszublenden.',
    accentLabel: 'Mobil ohne Auto',
    theme: {
      cardClass: 'border-indigo-200 bg-indigo-50/60 hover:border-indigo-300 hover:bg-indigo-50',
      activeClass: 'border-indigo-500 bg-indigo-100 shadow-sm ring-2 ring-indigo-100',
      badgeClass: 'bg-indigo-100 text-indigo-800',
      dotClass: 'bg-indigo-500'
    },
    weights: {
      climate_weight: 2,
      air_weight: 3,
      safety_weight: 3,
      demographics_weight: 1,
      amenities_weight: 4,
      landuse_weight: 2,
      oepnv_weight: 5
    }
  },
  {
    key: 'air-climate',
    label: 'Gute Luft & Klima',
    description: 'Legt den Schwerpunkt auf Luftqualität und klimatische Belastung.',
    accentLabel: 'Luft + Klima',
    theme: {
      cardClass: 'border-sky-200 bg-sky-50/60 hover:border-sky-300 hover:bg-sky-50',
      activeClass: 'border-sky-500 bg-sky-100 shadow-sm ring-2 ring-sky-100',
      badgeClass: 'bg-sky-100 text-sky-800',
      dotClass: 'bg-sky-500'
    },
    weights: {
      climate_weight: 5,
      air_weight: 5,
      safety_weight: 2,
      demographics_weight: 1,
      amenities_weight: 2,
      landuse_weight: 3,
      oepnv_weight: 2
    }
  },
  {
    key: 'urban',
    label: 'Urban & alltagsnah',
    description: 'Sucht Orte mit dichter Versorgung und starkem ÖPNV-Angebot.',
    accentLabel: 'Stadt + Versorgung',
    theme: {
      cardClass: 'border-emerald-200 bg-emerald-50/60 hover:border-emerald-300 hover:bg-emerald-50',
      activeClass: 'border-emerald-500 bg-emerald-100 shadow-sm ring-2 ring-emerald-100',
      badgeClass: 'bg-emerald-100 text-emerald-800',
      dotClass: 'bg-emerald-500'
    },
    weights: {
      climate_weight: 2,
      air_weight: 2,
      safety_weight: 2,
      demographics_weight: 2,
      amenities_weight: 5,
      landuse_weight: 1,
      oepnv_weight: 5
    }
  },
  {
    key: 'quiet-nature',
    label: 'Ruhig & naturnah',
    description: 'Gewichtet Klima, Luft und Flächennutzung höher als urbane Dichte.',
    accentLabel: 'Natur + Ruhe',
    theme: {
      cardClass: 'border-lime-200 bg-lime-50/60 hover:border-lime-300 hover:bg-lime-50',
      activeClass: 'border-lime-500 bg-lime-100 shadow-sm ring-2 ring-lime-100',
      badgeClass: 'bg-lime-100 text-lime-800',
      dotClass: 'bg-lime-500'
    },
    weights: {
      climate_weight: 4,
      air_weight: 4,
      safety_weight: 3,
      demographics_weight: 1,
      amenities_weight: 2,
      landuse_weight: 5,
      oepnv_weight: 2
    }
  }
]

export const finderPresetMap = Object.fromEntries(
  finderPresets.map((preset) => [preset.key, preset])
) as Record<FinderPresetKey, FinderPresetDefinition>

export function findMatchingPresetKey(input: RecommendationInput): FinderPresetKey | null {
  for (const preset of finderPresets) {
    const matches = Object.entries(preset.weights).every(
      ([key, value]) => input[key as WeightKey] === value
    )
    if (matches) {
      return preset.key
    }
  }
  return null
}

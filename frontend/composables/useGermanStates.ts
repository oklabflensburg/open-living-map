export interface GermanStateOption {
  code: string
  name: string
  slug: string
}

export const germanStates: GermanStateOption[] = [
  { code: '01', name: 'Schleswig-Holstein', slug: 'schleswig-holstein' },
  { code: '02', name: 'Hamburg', slug: 'hamburg' },
  { code: '03', name: 'Niedersachsen', slug: 'niedersachsen' },
  { code: '04', name: 'Bremen', slug: 'bremen' },
  { code: '05', name: 'Nordrhein-Westfalen', slug: 'nordrhein-westfalen' },
  { code: '06', name: 'Hessen', slug: 'hessen' },
  { code: '07', name: 'Rheinland-Pfalz', slug: 'rheinland-pfalz' },
  { code: '08', name: 'Baden-Württemberg', slug: 'baden-wuerttemberg' },
  { code: '09', name: 'Bayern', slug: 'bayern' },
  { code: '10', name: 'Saarland', slug: 'saarland' },
  { code: '11', name: 'Berlin', slug: 'berlin' },
  { code: '12', name: 'Brandenburg', slug: 'brandenburg' },
  { code: '13', name: 'Mecklenburg-Vorpommern', slug: 'mecklenburg-vorpommern' },
  { code: '14', name: 'Sachsen', slug: 'sachsen' },
  { code: '15', name: 'Sachsen-Anhalt', slug: 'sachsen-anhalt' },
  { code: '16', name: 'Thüringen', slug: 'thueringen' }
]

export const germanyRankingScope = {
  code: null,
  name: 'Deutschland',
  slug: 'deutschland'
} as const

export function getGermanStateByCode(stateCode: string | null | undefined) {
  if (!stateCode) {
    return null
  }

  return germanStates.find((state) => state.code === stateCode) || null
}

export function getGermanStateBySlug(stateSlug: string | null | undefined) {
  if (!stateSlug || stateSlug === germanyRankingScope.slug) {
    return null
  }

  return germanStates.find((state) => state.slug === stateSlug) || null
}

export function getGermanStateName(stateCode: string | null | undefined) {
  if (!stateCode) {
    return 'Deutschlandweit'
  }

  return germanStates.find((state) => state.code === stateCode)?.name || 'Unbekanntes Bundesland'
}
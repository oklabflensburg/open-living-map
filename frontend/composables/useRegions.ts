import type {
  GeoJsonFeatureCollection,
  RegionDetailResponse,
  RegionListResponse
} from '~/types/api'

export function useRegions() {
  const { apiFetch } = useApi()

  const fetchRegions = async (params?: {
    q?: string
    state_code?: string | null
    limit?: number
    offset?: number
  }): Promise<RegionListResponse> => {
    return await apiFetch<RegionListResponse>('/regions', {
      query: params
    })
  }

  const searchRegionsAutocomplete = async (q: string, limit = 8): Promise<RegionListResponse> => {
    return await apiFetch<RegionListResponse>('/regions/search/autocomplete', {
      query: { q, limit }
    })
  }

  const fetchRegion = async (ars: string): Promise<RegionDetailResponse> => {
    return await apiFetch<RegionDetailResponse>(`/regions/${ars}`)
  }

  const fetchAmenityPois = async (ars: string, category: string): Promise<GeoJsonFeatureCollection> => {
    return await apiFetch<GeoJsonFeatureCollection>(`/regions/${ars}/amenities/${category}`)
  }

  const fetchAccidentPois = async (ars: string, category: string): Promise<GeoJsonFeatureCollection> => {
    return await apiFetch<GeoJsonFeatureCollection>(`/regions/${ars}/accidents/${category}`)
  }

  const fetchStateBoundaries = async (stateCode: string | null): Promise<GeoJsonFeatureCollection> => {
    const query = stateCode ? `?state_code=${encodeURIComponent(stateCode)}` : ''
    return await apiFetch<GeoJsonFeatureCollection>(`/regions/state-boundaries${query}`)
  }

  return { fetchRegions, searchRegionsAutocomplete, fetchRegion, fetchAmenityPois, fetchAccidentPois, fetchStateBoundaries }
}

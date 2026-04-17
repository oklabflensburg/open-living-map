import type { GeoJsonFeatureCollection, RegionDetailResponse, RegionListResponse } from '~/types/api'

export function useRegions() {
  const { apiFetch } = useApi()

  const fetchRegions = async (): Promise<RegionListResponse> => {
    return await apiFetch<RegionListResponse>('/regions')
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

  return { fetchRegions, fetchRegion, fetchAmenityPois, fetchAccidentPois }
}

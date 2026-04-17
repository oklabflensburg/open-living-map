import type { RecommendationInput, RecommendationResponse } from '~/types/api'

export function useRecommendations() {
  const { apiFetch } = useApi()

  const fetchRecommendations = async (payload: RecommendationInput): Promise<RecommendationResponse> => {
    return await apiFetch<RecommendationResponse>('/recommendations', {
      method: 'POST',
      body: payload
    })
  }

  const fetchCompare = async (ars: string[]): Promise<RecommendationResponse> => {
    return await apiFetch<RecommendationResponse>(`/compare?ars=${encodeURIComponent(ars.join(','))}`)
  }

  return { fetchRecommendations, fetchCompare }
}

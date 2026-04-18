import type { RecommendationInput, RecommendationResponse } from '~/types/api'
import type { RankingCategory } from '~/composables/useRankingCategories'

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

  const fetchTopRankings = async (
    category: RankingCategory,
    stateCode: string | null,
    limit = 100
  ): Promise<RecommendationResponse> => {
    const params = new URLSearchParams({
      limit: String(limit)
    })

    if (stateCode) {
      params.set('state_code', stateCode)
    }

    return await apiFetch<RecommendationResponse>(
      `/rankings/top/${encodeURIComponent(category)}?${params.toString()}`
    )
  }

  return { fetchRecommendations, fetchCompare, fetchTopRankings }
}

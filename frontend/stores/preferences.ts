import { defineStore } from 'pinia'
import { DEFAULT_FINDER_PREFERENCES, type FinderPreferences } from '~/composables/usePreferenceQuery'
import type { RecommendationInput } from '~/types/api'
import type { WeightKey } from '~/utils/recommendationConfig'

export const usePreferencesStore = defineStore('preferences', {
  state: (): FinderPreferences => ({ ...DEFAULT_FINDER_PREFERENCES }),
  actions: {
    setWeight(key: WeightKey, value: number) {
      this[key] = value
    },
    setStateCode(value: string | null) {
      this.state_code = value
    },
    setFilters(value: Partial<Pick<
      RecommendationInput,
      | 'min_climate_score'
      | 'min_air_score'
      | 'min_safety_score'
      | 'min_demographics_score'
      | 'min_amenities_score'
      | 'min_landuse_score'
      | 'min_oepnv_score'
      | 'coverage_min'
    >>) {
      this.$patch(value)
    }
  }
})

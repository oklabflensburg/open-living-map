import { defineStore } from 'pinia'
import type { RecommendationInput } from '~/types/api'

export const usePreferencesStore = defineStore('preferences', {
  state: (): RecommendationInput => ({
    climate_weight: 5,
    air_weight: 4,
    safety_weight: 3,
    demographics_weight: 4,
    amenities_weight: 5,
    landuse_weight: 3,
    oepnv_weight: 4,
    state_code: null
  }),
  actions: {
    setWeight(key: keyof Omit<RecommendationInput, 'state_code'>, value: number) {
      this[key] = value
    },
    setStateCode(value: string | null) {
      this.state_code = value
    }
  }
})

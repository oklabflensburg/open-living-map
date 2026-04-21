import { defineStore } from 'pinia'
import { DEFAULT_PREFERENCES } from '~/composables/usePreferenceQuery'
import type { RecommendationInput } from '~/types/api'

export const usePreferencesStore = defineStore('preferences', {
  state: (): RecommendationInput => ({ ...DEFAULT_PREFERENCES }),
  actions: {
    setWeight(key: keyof Omit<RecommendationInput, 'state_code'>, value: number) {
      this[key] = value
    },
    setStateCode(value: string | null) {
      this.state_code = value
    }
  }
})

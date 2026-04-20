import { defineStore } from 'pinia'
import type { Region } from '~/types/api'

const STORAGE_KEY = 'wohnortkompass.compare'

interface CompareState {
  search_query: string
  selected_regions: Region[]
}

function persistState(state: CompareState) {
  if (!import.meta.client) {
    return
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export const useCompareStore = defineStore('compare', {
  state: (): CompareState => ({
    search_query: '',
    selected_regions: []
  }),
  actions: {
    hydrate() {
      if (!import.meta.client) {
        return
      }
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) {
        return
      }
      try {
        const parsed = JSON.parse(raw) as Partial<CompareState>
        this.search_query = typeof parsed.search_query === 'string' ? parsed.search_query : ''
        this.selected_regions = Array.isArray(parsed.selected_regions) ? parsed.selected_regions.slice(0, 3) : []
      } catch {
        this.search_query = ''
        this.selected_regions = []
      }
    },
    setSearchQuery(value: string) {
      this.search_query = value
      persistState(this.$state)
    },
    addRegion(region: Region) {
      if (this.selected_regions.some((item) => item.ars === region.ars) || this.selected_regions.length >= 3) {
        return
      }
      this.selected_regions = [...this.selected_regions, region]
      persistState(this.$state)
    },
    setSelectedRegions(regions: Region[]) {
      this.selected_regions = regions.slice(0, 3)
      persistState(this.$state)
    },
    removeRegion(ars: string) {
      this.selected_regions = this.selected_regions.filter((item) => item.ars !== ars)
      persistState(this.$state)
    },
    popRegion() {
      this.selected_regions = this.selected_regions.slice(0, -1)
      persistState(this.$state)
    },
    clearSearchQuery() {
      this.search_query = ''
      persistState(this.$state)
    }
  }
})

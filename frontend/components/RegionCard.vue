<template>
  <article class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div class="mb-2 flex items-start justify-between gap-4">
      <div>
        <h3 class="text-lg font-semibold">
          <NuxtLink :to="`/region/${item.slug}`" class="transition hover:text-blue-700">
            {{ item.name }}
          </NuxtLink>
        </h3>
        <p class="text-xs text-slate-500">{{ regionMetaLine(item) }}</p>
        <p class="mt-1 text-xs text-slate-500">
          Neutraler Gesamtscore: {{ item.score_total.toFixed(1) }}
        </p>
      </div>
      <div class="text-right">
        <span class="mt-1 inline-block rounded-lg bg-slate-100 px-2.5 py-1 text-sm font-semibold text-slate-800">
          {{ item.score_profile.toFixed(1) }}
        </span>
      </div>
    </div>

    <div class="space-y-2 sm:hidden">
      <ScoreBar
        v-for="category in mobileCategories"
        :key="category.key"
        :label="category.label"
        :value="category.value"
        :card-class="category.cardClass"
        :badge-class="category.badgeClass"
        :bar-class="category.barClass"
      />
    </div>

    <div class="hidden space-y-2 sm:block">
      <ScoreBar
        label="Klima"
        :value="item.score_climate"
        card-class="border-amber-200 bg-amber-50/70"
        badge-class="bg-amber-100 text-amber-800"
        bar-class="bg-amber-600"
      />
      <ScoreBar
        label="Luft"
        :value="item.score_air"
        card-class="border-sky-200 bg-sky-50/70"
        badge-class="bg-sky-100 text-sky-800"
        bar-class="bg-sky-600"
      />
      <ScoreBar
        label="Verkehrssicherheit"
        :value="item.score_safety"
        card-class="border-rose-200 bg-rose-50/70"
        badge-class="bg-rose-100 text-rose-800"
        bar-class="bg-rose-600"
      />
      <ScoreBar
        label="Demografie"
        :value="item.score_demographics"
        card-class="border-violet-200 bg-violet-50/70"
        badge-class="bg-violet-100 text-violet-800"
        bar-class="bg-violet-600"
      />
      <ScoreBar
        label="Alltagsnähe"
        :value="item.score_amenities"
        card-class="border-emerald-200 bg-emerald-50/70"
        badge-class="bg-emerald-100 text-emerald-800"
        bar-class="bg-emerald-600"
      />
      <ScoreBar
        label="Flächennutzung"
        :value="item.score_landuse"
        card-class="border-orange-200 bg-orange-50/70"
        badge-class="bg-orange-100 text-orange-800"
        bar-class="bg-orange-600"
      />
      <ScoreBar
        label="ÖPNV"
        :value="item.score_oepnv"
        card-class="border-indigo-200 bg-indigo-50/70"
        badge-class="bg-indigo-100 text-indigo-800"
        bar-class="bg-indigo-600"
      />
    </div>

    <p v-if="showProfileContext" class="mt-3 text-sm text-slate-600">{{ item.reason }}</p>

    <ResultDeltaSummary
      v-if="deltaReference"
      class="mt-3"
      :item="item"
      :reference="deltaReference"
      :title="deltaTitle"
    />

    <NuxtLink :to="`/region/${item.slug}`" class="mt-3 inline-block text-sm font-semibold text-blue-700">
      Details ansehen
    </NuxtLink>
  </article>
</template>

<script setup lang="ts">
import ResultDeltaSummary from '~/components/ResultDeltaSummary.vue'
import type { RecommendationInput, RecommendationItem } from '~/types/api'
import { getCategoryScore, getCategoryWeight, recommendationCategories } from '~/utils/recommendationConfig'

import ScoreBar from './ScoreBar.vue'

const props = withDefaults(defineProps<{
  item: RecommendationItem
  showProfileContext?: boolean
  profilePreferences?: RecommendationInput | null
  deltaReference?: RecommendationItem | null
  deltaTitle?: string
}>(), {
  showProfileContext: true,
  profilePreferences: null,
  deltaReference: null,
  deltaTitle: 'Warum dieses Ergebnis?'
})

const allCategories = computed(() => recommendationCategories.map((category) => ({
  ...category,
  value: getCategoryScore(props.item, category.key),
  weight: props.profilePreferences ? getCategoryWeight(props.profilePreferences, category.key) : 0
})))

const mobileCategories = computed(() => {
  const categories = [...allCategories.value]
  if (!props.profilePreferences) {
    return categories.sort((left, right) => right.value - left.value).slice(0, 3)
  }

  return categories
    .sort((left, right) => {
      if (right.weight !== left.weight) {
        return right.weight - left.weight
      }
      return right.value - left.value
    })
    .slice(0, 3)
})

function regionMetaLine(item: RecommendationItem) {
  return [
    `AGS ${item.ars}`,
    item.state_name,
    item.district_name
  ].filter(Boolean).join(' · ')
}
</script>

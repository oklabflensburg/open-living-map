<template>
  <article class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div class="mb-2 flex items-start justify-between gap-4">
      <div>
        <h3 class="text-lg font-semibold">
          <NuxtLink :to="`/region/${item.slug}`" class="transition hover:text-blue-700">
            {{ item.name }}
          </NuxtLink>
        </h3>
        <p class="text-xs text-slate-500">AGS: {{ item.ars }}</p>
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

    <div class="space-y-2">
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

    <details class="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
      <summary class="cursor-pointer font-semibold text-slate-900">
        {{ showProfileContext ? 'Berechnung und Datenbasis anzeigen' : 'Vergleichsdaten anzeigen' }}
      </summary>

      <div class="mt-3 space-y-3">
        <div v-if="showProfileContext">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Score-Formel</p>
          <p class="mt-1">{{ item.score_formula }}</p>
        </div>

        <div v-if="showProfileContext">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Warum dieses Ergebnis?</p>
          <ul class="mt-1 list-disc space-y-1 pl-5">
            <li v-for="detail in item.calculation_details" :key="detail">{{ detail }}</li>
          </ul>
        </div>

        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Datenabdeckung</p>
          <p class="mt-1 text-xs text-slate-600">
            {{ coverageText(item) }}
          </p>
        </div>

        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Rohdaten und Teil-Scores</p>
          <div class="mt-2 grid gap-2">
            <div
              v-for="indicator in item.indicators"
              :key="indicator.key"
              class="rounded-lg border p-2"
              :class="indicatorCategoryTheme(indicator.category).cardClass"
            >
              <div class="flex items-start justify-between gap-3">
                <p class="font-medium">{{ indicator.name }}</p>
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-semibold"
                  :class="indicatorCategoryTheme(indicator.category).badgeClass"
                >
                  {{ categoryLabel(indicator.category) }}
                </span>
              </div>
              <p class="mt-1 text-xs text-slate-700">{{ indicator.text }}</p>
              <p v-if="indicator.quality_flag !== 'ok'" class="mt-1 text-xs text-amber-700">
                Datenqualität: {{ indicator.quality_flag }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </details>

    <NuxtLink :to="`/region/${item.slug}`" class="mt-3 inline-block text-sm font-semibold text-blue-700">
      Details ansehen
    </NuxtLink>
  </article>
</template>

<script setup lang="ts">
import type { RecommendationItem } from '~/types/api'

import ScoreBar from './ScoreBar.vue'

withDefaults(defineProps<{
  item: RecommendationItem
  showProfileContext?: boolean
}>(), {
  showProfileContext: true
})

const categoryLabels: Record<string, string> = {
  climate: 'Klima',
  air: 'Luftqualität',
  safety: 'Verkehrssicherheit',
  demographics: 'Demografie/Familie',
  amenities: 'Alltagsnähe',
  landuse: 'Flächennutzung',
  oepnv: 'ÖPNV'
}

const categoryThemes: Record<string, { cardClass: string; badgeClass: string }> = {
  climate: {
    cardClass: 'border-amber-200 bg-amber-50/70',
    badgeClass: 'bg-amber-100 text-amber-800'
  },
  air: {
    cardClass: 'border-sky-200 bg-sky-50/70',
    badgeClass: 'bg-sky-100 text-sky-800'
  },
  safety: {
    cardClass: 'border-rose-200 bg-rose-50/70',
    badgeClass: 'bg-rose-100 text-rose-800'
  },
  demographics: {
    cardClass: 'border-violet-200 bg-violet-50/70',
    badgeClass: 'bg-violet-100 text-violet-800'
  },
  amenities: {
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    badgeClass: 'bg-emerald-100 text-emerald-800'
  },
  landuse: {
    cardClass: 'border-orange-200 bg-orange-50/70',
    badgeClass: 'bg-orange-100 text-orange-800'
  },
  oepnv: {
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    badgeClass: 'bg-indigo-100 text-indigo-800'
  }
}

function categoryLabel(category: string) {
  return categoryLabels[category] || category
}

function indicatorCategoryTheme(category: string) {
  return categoryThemes[category] || {
    cardClass: 'border-slate-200 bg-white',
    badgeClass: 'bg-slate-100 text-slate-700'
  }
}

function coverageText(item: RecommendationItem) {
  const entries: Array<[string, number]> = [
    ['Klima', item.coverage_climate],
    ['Luftqualität', item.coverage_air],
    ['Verkehrssicherheit', item.coverage_safety],
    ['Demografie/Familie', item.coverage_demographics],
    ['Alltagsnähe', item.coverage_amenities],
    ['Flächennutzung', item.coverage_landuse],
    ['ÖPNV', item.coverage_oepnv]
  ]
  const coverageValues = entries.map(([, coverage]) => coverage)
  const hasCoverageMetadata = coverageValues.some((coverage) => coverage > 0)

  if (!hasCoverageMetadata) {
    return 'Für diesen Datenstand liegen noch keine separat berechneten Abdeckungswerte vor.'
  }

  return entries
    .filter(([, coverage]) => coverage < 1)
    .map(([label, coverage]) => `${label} ${Math.round(coverage * 100)} %`)
    .join(' · ') || 'Alle Kategorien sind vollständig mit Daten abgedeckt.'
}
</script>

<template>
  <article class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div class="mb-2 flex items-start justify-between gap-4">
      <div>
        <h3 class="text-lg font-semibold">{{ item.name }}</h3>
        <p class="text-xs text-slate-500">AGS: {{ item.ars }}</p>
      </div>
      <span class="rounded bg-blue-100 px-2 py-1 text-sm font-semibold text-blue-800">
        {{ item.score_total.toFixed(1) }}
      </span>
    </div>

    <div class="space-y-2">
      <ScoreBar label="Klima" :value="item.score_climate" />
      <ScoreBar label="Luft" :value="item.score_air" />
      <ScoreBar label="Sicherheit" :value="item.score_safety" />
      <ScoreBar label="Demografie" :value="item.score_demographics" />
      <ScoreBar label="Alltagsnaehe" :value="item.score_amenities" />
      <ScoreBar label="OEPNV" :value="item.score_oepnv" />
    </div>

    <p class="mt-3 text-sm text-slate-600">{{ item.reason }}</p>

    <details class="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
      <summary class="cursor-pointer font-semibold text-slate-900">
        Berechnung und Datenbasis anzeigen
      </summary>

      <div class="mt-3 space-y-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Score-Formel</p>
          <p class="mt-1">{{ item.score_formula }}</p>
        </div>

        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Warum dieses Ergebnis?</p>
          <ul class="mt-1 list-disc space-y-1 pl-5">
            <li v-for="detail in item.calculation_details" :key="detail">{{ detail }}</li>
          </ul>
        </div>

        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Rohdaten und Teil-Scores</p>
          <div class="mt-2 grid gap-2">
            <div
              v-for="indicator in item.indicators"
              :key="indicator.key"
              class="rounded border border-slate-200 bg-white p-2"
            >
              <div class="flex items-start justify-between gap-3">
                <p class="font-medium">{{ indicator.name }}</p>
                <span class="text-xs text-slate-500">{{ categoryLabel(indicator.category) }}</span>
              </div>
              <p class="mt-1 text-xs text-slate-600">{{ indicator.text }}</p>
              <p v-if="indicator.quality_flag !== 'ok'" class="mt-1 text-xs text-amber-700">
                Datenqualitaet: {{ indicator.quality_flag }}
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

defineProps<{ item: RecommendationItem }>()

const categoryLabels: Record<string, string> = {
  climate: 'Klima',
  air: 'Luft',
  safety: 'Sicherheit',
  demographics: 'Demografie',
  amenities: 'Alltagsnaehe',
  oepnv: 'OEPNV'
}

function categoryLabel(category: string) {
  return categoryLabels[category] || category
}
</script>

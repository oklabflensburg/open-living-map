<template>
  <section v-if="delta" class="rounded-lg border border-blue-100 bg-blue-50/70 p-3 text-sm text-slate-800">
    <p class="text-xs font-semibold uppercase tracking-wide text-blue-700">{{ title }}</p>
    <p class="mt-1">{{ delta.summary }}</p>
    <div v-if="delta.strengths.length || delta.weaknesses.length" class="mt-3 grid gap-2 sm:grid-cols-2">
      <div v-if="delta.strengths.length">
        <p class="text-xs font-semibold text-emerald-700">Stärker</p>
        <ul class="mt-1 space-y-1 text-xs">
          <li v-for="entry in delta.strengths" :key="entry.label">
            {{ entry.label }} +{{ entry.difference.toFixed(1) }}
          </li>
        </ul>
      </div>
      <div v-if="delta.weaknesses.length">
        <p class="text-xs font-semibold text-amber-700">Schwächer</p>
        <ul class="mt-1 space-y-1 text-xs">
          <li v-for="entry in delta.weaknesses" :key="entry.label">
            {{ entry.label }} {{ entry.difference.toFixed(1) }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { RecommendationItem } from '~/types/api'
import { buildResultDeltaExplanation } from '~/utils/resultDelta'

const props = defineProps<{
  item: RecommendationItem
  reference: RecommendationItem | null
  title: string
}>()

const delta = computed(() => buildResultDeltaExplanation(props.item, props.reference))
</script>

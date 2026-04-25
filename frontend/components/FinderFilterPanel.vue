<template>
  <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
    <div class="border-b border-slate-100 bg-slate-50/80 px-5 py-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Treffermenge</p>
          <h2 class="mt-1 text-base font-semibold text-slate-950">{{ title }}</h2>
          <p class="mt-1 text-sm leading-5 text-slate-600">
            Optional eingrenzen. Die Gewichtungen bestimmen danach die Sortierung.
          </p>
        </div>
        <button
          type="button"
          class="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-200"
          @click="resetFilters"
        >
          Zurücksetzen
        </button>
      </div>
    </div>

    <div class="space-y-5 p-5">
      <div class="grid gap-3">
        <div class="rounded-xl border border-slate-200 bg-white p-3">
          <StateSelect
            :model-value="modelValue.state_code"
            select-id="filter-state-select"
            label="Bundesland begrenzen"
            hint="Leer lassen, wenn alle Bundesländer berücksichtigt werden sollen."
            @update:model-value="update({ state_code: $event })"
          />
        </div>

        <label class="block rounded-xl border border-slate-200 bg-white p-3">
          <span class="text-sm font-semibold text-slate-900">Datenabdeckung</span>
          <span class="mt-1 block text-xs leading-5 text-slate-500">
            Blendet Orte mit sehr dünner Datenbasis aus.
          </span>
          <select
            :value="modelValue.coverage_min ?? ''"
            class="mt-3 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 transition focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-100"
            @change="updateNumber('coverage_min', $event)"
          >
            <option value="">Keine Mindestabdeckung</option>
            <option value="25">mind. 25 %</option>
            <option value="50">mind. 50 %</option>
            <option value="75">mind. 75 %</option>
          </select>
        </label>
      </div>

      <div>
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-semibold text-slate-900">Ausschlussgrenzen pro Thema</h3>
            <p class="mt-1 text-xs leading-5 text-slate-500">
              Diese Werte sind harte Filter: Orte darunter werden ausgeschlossen. Für Vorlieben besser die Gewichte nutzen.
            </p>
          </div>
          <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
            optional
          </span>
        </div>

        <div class="mt-3 grid gap-2">
          <label
            v-for="category in recommendationCategories"
            :key="category.key"
            class="grid grid-cols-[minmax(0,1fr)_8rem] items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2"
          >
            <span class="min-w-0">
              <span class="block truncate text-sm font-medium text-slate-900">{{ category.label }}</span>
            </span>
            <select
              :value="modelValue[category.minScoreKey] ?? ''"
              class="w-full rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-900 transition focus:border-blue-400 focus:outline-none focus:ring-4 focus:ring-blue-100"
              @change="updateNumber(category.minScoreKey, $event)"
            >
              <option value="">nicht ausschließen</option>
              <option value="40">unter 40 ausschließen</option>
              <option value="60">unter 60 ausschließen</option>
              <option value="75">unter 75 ausschließen</option>
              <option value="85">unter 85 ausschließen</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import StateSelect from '~/components/StateSelect.vue'
import type { FinderPreferences } from '~/composables/usePreferenceQuery'
import { recommendationCategories, type MinScoreKey } from '~/utils/recommendationConfig'

const props = defineProps<{
  modelValue: FinderPreferences
  title?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: FinderPreferences]
}>()

function update(value: Partial<FinderPreferences>) {
  emit('update:modelValue', {
    ...props.modelValue,
    ...value
  })
}

function updateNumber(key: MinScoreKey | 'coverage_min', event: Event) {
  const target = event.target as HTMLSelectElement
  update({
    [key]: target.value === '' ? null : Number(target.value)
  })
}

function resetFilters() {
  update({
    state_code: null,
    min_climate_score: null,
    min_air_score: null,
    min_safety_score: null,
    min_demographics_score: null,
    min_amenities_score: null,
    min_landuse_score: null,
    min_oepnv_score: null,
    coverage_min: null
  })
}
</script>

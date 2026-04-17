<template>
  <form class="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" @submit.prevent="$emit('submit')">
    <div class="space-y-2">
      <label class="font-medium" for="state-select">Bundesland</label>
      <select
        id="state-select"
        :value="modelValue.state_code || ''"
        class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
        @change="onStateChange"
      >
        <option value="">Deutschlandweit</option>
        <option v-for="state in states" :key="state.code" :value="state.code">
          {{ state.name }}
        </option>
      </select>
      <p class="text-xs text-slate-500">
        Die Empfehlungen werden nur innerhalb des gewählten Bundeslands berechnet.
      </p>
    </div>

    <div v-for="field in fields" :key="field.key" class="space-y-2">
      <div class="flex items-center justify-between">
        <label class="font-medium">{{ field.label }}</label>
        <span class="text-sm text-slate-500">{{ modelValue[field.key] }}</span>
      </div>
      <input
        :value="modelValue[field.key]"
        type="range"
        min="0"
        max="5"
        class="w-full"
        @input="onInput(field.key, $event)"
      >
    </div>

    <button class="w-full rounded bg-blue-700 px-4 py-2 font-semibold text-white hover:bg-blue-800" type="submit">
      Empfehlungen berechnen
    </button>
  </form>
</template>

<script setup lang="ts">
import type { RecommendationInput } from '~/types/api'

const props = defineProps<{ modelValue: RecommendationInput }>()
const emit = defineEmits<{
  'update:modelValue': [value: RecommendationInput]
  submit: []
}>()

const states = [
  { code: '01', name: 'Schleswig-Holstein' },
  { code: '02', name: 'Hamburg' },
  { code: '03', name: 'Niedersachsen' },
  { code: '04', name: 'Bremen' },
  { code: '05', name: 'Nordrhein-Westfalen' },
  { code: '06', name: 'Hessen' },
  { code: '07', name: 'Rheinland-Pfalz' },
  { code: '08', name: 'Baden-Wuerttemberg' },
  { code: '09', name: 'Bayern' },
  { code: '10', name: 'Saarland' },
  { code: '11', name: 'Berlin' },
  { code: '12', name: 'Brandenburg' },
  { code: '13', name: 'Mecklenburg-Vorpommern' },
  { code: '14', name: 'Sachsen' },
  { code: '15', name: 'Sachsen-Anhalt' },
  { code: '16', name: 'Thueringen' }
]

const fields: Array<{ key: keyof Omit<RecommendationInput, 'state_code'>; label: string }> = [
  { key: 'climate_weight', label: 'Klima' },
  { key: 'air_weight', label: 'Luftqualitaet' },
  { key: 'safety_weight', label: 'Verkehrssicherheit' },
  { key: 'demographics_weight', label: 'Demografie/Familie' },
  { key: 'amenities_weight', label: 'Alltagsnaehe' },
  { key: 'oepnv_weight', label: 'OEPNV' }
]

function onInput(key: keyof Omit<RecommendationInput, 'state_code'>, event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: Number(target.value)
  })
}

function onStateChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', {
    ...props.modelValue,
    state_code: target.value || null
  })
}
</script>

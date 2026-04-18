<template>
  <form class="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" @submit.prevent="$emit('submit')">
    <StateSelect
      :model-value="modelValue.state_code"
      hint="Die Empfehlungen werden nur innerhalb des gewählten Bundeslands berechnet."
      @update:model-value="onStateChange"
    />

    <div v-for="field in fields" :key="field.key" class="space-y-3 rounded-xl border p-4" :class="field.cardClass">
      <div class="flex items-center justify-between">
        <label class="font-medium text-slate-900">{{ field.label }}</label>
        <span class="rounded-full px-2.5 py-1 text-sm font-semibold" :class="field.badgeClass">{{ modelValue[field.key] }}</span>
      </div>
      <input
        :value="modelValue[field.key]"
        type="range"
        min="0"
        max="5"
        class="slider h-2 w-full cursor-pointer appearance-none rounded-full"
        :style="{
          background: `linear-gradient(to right, ${field.color} 0%, ${field.color} ${(modelValue[field.key] / 5) * 100}%, #dbe3ef ${(modelValue[field.key] / 5) * 100}%, #dbe3ef 100%)`
        }"
        @input="onInput(field.key, $event)"
      >
      <div class="flex justify-between text-[11px] font-medium text-slate-500">
        <span>unwichtig</span>
        <span>neutral</span>
        <span>sehr wichtig</span>
      </div>
    </div>

    <button class="w-full rounded bg-blue-700 px-4 py-2 font-semibold text-white hover:bg-blue-800" type="submit">
      Empfehlungen berechnen
    </button>
  </form>
</template>

<script setup lang="ts">
import StateSelect from '~/components/StateSelect.vue'
import type { RecommendationInput } from '~/types/api'

const props = defineProps<{ modelValue: RecommendationInput }>()
const emit = defineEmits<{
  'update:modelValue': [value: RecommendationInput]
  submit: []
}>()

const fields: Array<{
  key: keyof Omit<RecommendationInput, 'state_code'>
  label: string
  color: string
  cardClass: string
  badgeClass: string
}> = [
  {
    key: 'climate_weight',
    label: 'Klima',
    color: '#d97706',
    cardClass: 'border-amber-200 bg-amber-50/70',
    badgeClass: 'bg-amber-100 text-amber-800'
  },
  {
    key: 'air_weight',
    label: 'Luftqualität',
    color: '#0284c7',
    cardClass: 'border-sky-200 bg-sky-50/70',
    badgeClass: 'bg-sky-100 text-sky-800'
  },
  {
    key: 'safety_weight',
    label: 'Verkehrssicherheit',
    color: '#e11d48',
    cardClass: 'border-rose-200 bg-rose-50/70',
    badgeClass: 'bg-rose-100 text-rose-800'
  },
  {
    key: 'demographics_weight',
    label: 'Demografie/Familie',
    color: '#7c3aed',
    cardClass: 'border-violet-200 bg-violet-50/70',
    badgeClass: 'bg-violet-100 text-violet-800'
  },
  {
    key: 'amenities_weight',
    label: 'Alltagsnähe',
    color: '#059669',
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    badgeClass: 'bg-emerald-100 text-emerald-800'
  },
  {
    key: 'oepnv_weight',
    label: 'ÖPNV',
    color: '#4f46e5',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    badgeClass: 'bg-indigo-100 text-indigo-800'
  }
]

function onInput(key: keyof Omit<RecommendationInput, 'state_code'>, event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: Number(target.value)
  })
}

function onStateChange(value: string | null) {
  emit('update:modelValue', {
    ...props.modelValue,
    state_code: value
  })
}
</script>

<style scoped>
.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 1rem;
  height: 1rem;
  border-radius: 9999px;
  background: #0f172a;
  border: 2px solid #ffffff;
  box-shadow: 0 1px 4px rgb(15 23 42 / 0.25);
}

.slider::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  border-radius: 9999px;
  background: #0f172a;
  border: 2px solid #ffffff;
  box-shadow: 0 1px 4px rgb(15 23 42 / 0.25);
}
</style>

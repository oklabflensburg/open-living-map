<template>
  <form class="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" @submit.prevent="$emit('submit')">
    <section class="space-y-3">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div class="min-w-0">
          <h2 class="font-semibold text-slate-900">Profil wählen</h2>
          <p class="mt-1 text-sm text-slate-600">Ein Preset ist ein Startpunkt. Regler bleiben frei anpassbar.</p>
        </div>
        <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="activePresetTheme.badgeClass">
          {{ activePresetLabel }}
        </span>
      </div>

      <div class="grid gap-2">
        <button
          v-for="preset in finderPresets"
          :key="preset.key"
          type="button"
          class="rounded-lg border p-3 text-left transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-200"
          :class="activePresetKey === preset.key ? preset.theme.activeClass : preset.theme.cardClass"
          :aria-pressed="activePresetKey === preset.key"
          @click="applyPreset(preset.key)"
        >
          <span class="flex items-start gap-3">
            <span class="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" :class="preset.theme.dotClass" />
            <span class="min-w-0">
              <span class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-semibold text-slate-900">{{ preset.label }}</span>
                <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="preset.theme.badgeClass">
                  {{ preset.accentLabel }}
                </span>
              </span>
              <span class="mt-1 block text-xs leading-5 text-slate-600">{{ preset.description }}</span>
            </span>
          </span>
        </button>
      </div>
      <button
        type="button"
        class="text-sm font-semibold text-blue-700 hover:text-blue-900"
        @click="switchToCustom"
      >
        Als individuelles Profil weiter bearbeiten
      </button>
    </section>

    <StateSelect
      :model-value="modelValue.state_code"
      select-id="preference-state-select"
      hint="Die Empfehlungen werden nur innerhalb des gewählten Bundeslands berechnet."
      @update:model-value="onStateChange"
    />

    <div class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h2 class="font-semibold text-slate-900">Gewichte feinjustieren</h2>
        <span class="text-xs font-medium text-slate-500">0 bis 5</span>
      </div>
      <div v-for="field in fields" :key="field.key" class="space-y-2 rounded-lg border px-3 py-3" :class="field.cardClass">
      <div class="flex items-center justify-between">
        <label class="font-medium text-slate-900" :for="sliderId(field.key)">{{ field.label }}</label>
        <span class="rounded-full px-2.5 py-1 text-sm font-semibold" :class="field.badgeClass">{{ modelValue[field.key] }}</span>
      </div>
      <input
        :id="sliderId(field.key)"
        :value="modelValue[field.key]"
        type="range"
        min="0"
        max="5"
        :aria-valuetext="`${modelValue[field.key]} von 5`"
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
    </div>

    <button class="w-full rounded-lg bg-blue-700 px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-200" type="submit">
      Empfehlungen berechnen
    </button>
  </form>
</template>

<script setup lang="ts">
import StateSelect from '~/components/StateSelect.vue'
import type { FinderPreferences } from '~/composables/usePreferenceQuery'
import { finderPresetMap, finderPresets, findMatchingPresetKey, type FinderPresetKey } from '~/utils/finderPresets'
import type { WeightKey } from '~/utils/recommendationConfig'

const props = defineProps<{ modelValue: FinderPreferences }>()
const emit = defineEmits<{
  'update:modelValue': [value: FinderPreferences]
  submit: []
}>()

const fields: Array<{
  key: WeightKey
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
    key: 'landuse_weight',
    label: 'Flächennutzung',
    color: '#b45309',
    cardClass: 'border-orange-200 bg-orange-50/70',
    badgeClass: 'bg-orange-100 text-orange-800'
  },
  {
    key: 'oepnv_weight',
    label: 'ÖPNV',
    color: '#4f46e5',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    badgeClass: 'bg-indigo-100 text-indigo-800'
  }
]

const matchingPresetKey = computed(() => findMatchingPresetKey(props.modelValue))
const activePresetKey = computed(() => {
  if (props.modelValue.preset && matchingPresetKey.value === props.modelValue.preset) {
    return props.modelValue.preset
  }
  return matchingPresetKey.value
})
const activePresetLabel = computed(() => {
  if (activePresetKey.value) {
    return finderPresetMap[activePresetKey.value].label
  }
  return 'Individuell'
})
const activePresetTheme = computed(() => {
  if (activePresetKey.value) {
    return finderPresetMap[activePresetKey.value].theme
  }

  return {
    badgeClass: 'bg-slate-100 text-slate-700'
  }
})

function applyPreset(key: FinderPresetKey) {
  emit('update:modelValue', {
    ...props.modelValue,
    ...finderPresetMap[key].weights,
    preset: key
  })
}

function switchToCustom() {
  emit('update:modelValue', {
    ...props.modelValue,
    preset: null
  })
}

function onInput(key: WeightKey, event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: Number(target.value),
    preset: null
  })
}

function onStateChange(value: string | null) {
  emit('update:modelValue', {
    ...props.modelValue,
    state_code: value
  })
}

function sliderId(key: WeightKey) {
  return `preference-${key.replace('_weight', '')}`
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

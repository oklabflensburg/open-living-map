<template>
  <div class="space-y-2">
    <label class="font-medium" :for="selectId">{{ label }}</label>
    <select
      :id="selectId"
      :value="modelValue || ''"
      class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
      @change="onChange"
    >
      <option value="">Deutschlandweit</option>
      <option v-for="state in germanStates" :key="state.code" :value="state.code">
        {{ state.name }}
      </option>
    </select>
    <p v-if="hint" class="text-xs text-slate-500">
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { germanStates } from '~/composables/useGermanStates'

withDefaults(
  defineProps<{
    modelValue: string | null
    label?: string
    hint?: string
    selectId?: string
  }>(),
  {
    label: 'Bundesland',
    hint: '',
    selectId: 'state-select'
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

function onChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value || null)
}
</script>
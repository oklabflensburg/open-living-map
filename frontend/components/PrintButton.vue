<template>
  <button
    type="button"
    class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
    @click="printPage"
  >
    {{ label || 'Drucken / PDF' }}
  </button>
</template>

<script setup lang="ts">
defineProps<{
  label?: string
}>()

function printPage() {
  window.print()
}
</script>

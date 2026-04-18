<template>
  <div class="rounded-xl border p-4 shadow-sm" :class="cardClass">
    <div class="mb-1 flex justify-between text-sm">
      <span class="font-medium text-slate-900">{{ label }}</span>
      <span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="badgeClass">{{ value.toFixed(1) }}</span>
    </div>
    <div class="h-2.5 w-full rounded-full bg-white/80">
      <div class="h-2.5 rounded-full" :class="barClass" :style="{ width: `${Math.max(0, Math.min(100, value))}%` }" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: number
    cardClass?: string
    badgeClass?: string
    barClass?: string
  }>(),
  {
    cardClass: 'border-slate-200 bg-white',
    badgeClass: 'bg-slate-100 text-slate-700',
    barClass: 'bg-blue-600'
  }
)
</script>

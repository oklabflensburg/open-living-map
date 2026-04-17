<template>
  <div>
    <div class="mb-1 flex justify-between text-sm">
      <span class="font-medium">{{ label }}</span>
      <span>{{ value.toFixed(1) }}</span>
    </div>
    <div class="h-2 w-full rounded-full bg-slate-200">
      <div class="h-2 rounded-full bg-blue-600" :style="{ width: `${Math.max(0, Math.min(100, value))}%` }" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: number }>()
</script>

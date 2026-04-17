<template>
  <ul class="space-y-2 text-sm">
    <li v-for="source in sources" :key="source">
      <a :href="source" target="_blank" class="text-blue-700 underline decoration-blue-300 underline-offset-2">
        {{ source }}
      </a>
    </li>
  </ul>
</template>

<script setup lang="ts">
defineProps<{ sources: string[] }>()
</script>

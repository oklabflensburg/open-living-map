<template>
  <section>
    <h1 class="mb-4 text-2xl font-bold">Regionen vergleichen</h1>

    <form class="mb-6 flex flex-col gap-3 md:flex-row" @submit.prevent="runCompare">
      <input
        v-model="arsInput"
        type="text"
        placeholder="z.B. 09162,06412,05315"
        class="w-full rounded border border-slate-300 px-3 py-2"
      >
      <button class="rounded bg-blue-700 px-4 py-2 font-semibold text-white">Vergleichen</button>
    </form>

    <div class="grid gap-4 md:grid-cols-3">
      <RegionCard v-for="item in items" :key="item.ars" :item="item" />
    </div>
  </section>
</template>

<script setup lang="ts">
import RegionCard from '~/components/RegionCard.vue'
import type { RecommendationItem } from '~/types/api'

const { fetchCompare } = useRecommendations()

const arsInput = ref('09162,06412,05315')
const items = ref<RecommendationItem[]>([])

async function runCompare() {
  const ars = arsInput.value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 3)

  if (!ars.length) {
    items.value = []
    return
  }

  const response = await fetchCompare(ars)
  items.value = response.items
}

onMounted(runCompare)
</script>

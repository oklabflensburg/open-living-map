<template>
  <section>
    <div class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Top Empfehlungen</h1>
        <p class="text-sm text-slate-500">
          Auswahl: {{ selectedStateName }}
        </p>
      </div>
      <div class="w-full max-w-sm space-y-3">
        <StateSelect
          :model-value="store.state_code"
          hint="Die Empfehlungen werden nur innerhalb des gewählten Bundeslands berechnet."
          @update:model-value="onStateChange"
        />
        <NuxtLink to="/finder" class="inline-block text-sm font-semibold text-blue-700">Gewichte anpassen</NuxtLink>
      </div>
    </div>

    <div class="mb-6">
      <RegionMap :items="response?.items || []" />
    </div>

    <div v-if="pending" class="text-slate-500">Lade Empfehlungen...</div>
    <div v-else-if="error" class="text-red-600">{{ error }}</div>
    <div v-else class="grid gap-4 md:grid-cols-2">
      <RegionCard v-for="item in response?.items" :key="item.ars" :item="item" />
    </div>
  </section>
</template>

<script setup lang="ts">
import RegionCard from '~/components/RegionCard.vue'
import RegionMap from '~/components/RegionMap.vue'
import StateSelect from '~/components/StateSelect.vue'
import { getGermanStateName } from '~/composables/useGermanStates'
import { usePreferencesStore } from '~/stores/preferences'
import type { RecommendationResponse } from '~/types/api'

const { siteName, absoluteUrl } = useSiteSeo()
const store = usePreferencesStore()
const { fetchRecommendations } = useRecommendations()

const pending = ref(true)
const error = ref('')
const response = ref<RecommendationResponse | null>(null)

const title = 'Ranking'
const description = 'Ergebnisse und Kartenansicht der berechneten Wohnort-Empfehlungen.'

useSeoMeta({
  title,
  description,
  robots: 'noindex,follow',
  ogUrl: absoluteUrl('/results'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'website',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

const selectedStateName = computed(() => getGermanStateName(store.state_code))

async function loadRecommendations() {
  pending.value = true
  error.value = ''

  try {
    response.value = await fetchRecommendations({ ...store.$state })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unbekannter Fehler'
  } finally {
    pending.value = false
  }
}

async function onStateChange(value: string | null) {
  store.setStateCode(value)
  await loadRecommendations()
}

useHead(() => {
  const items = (response.value?.items || []).slice(0, 10)
  return {
    link: [{ rel: 'canonical', href: absoluteUrl('/results') }],
    script: [
      {
        key: 'ld-results',
        type: 'application/ld+json',
        children: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'CollectionPage',
          name: `${title} | ${siteName}`,
          url: absoluteUrl('/results'),
          description,
          breadcrumb: {
            '@type': 'BreadcrumbList',
            itemListElement: [
              {
                '@type': 'ListItem',
                position: 1,
                name: 'Startseite',
                item: absoluteUrl('/')
              },
              {
                '@type': 'ListItem',
                position: 2,
                name: title,
                item: absoluteUrl('/results')
              }
            ]
          },
          mainEntity: {
            '@type': 'ItemList',
            itemListElement: items.map((item, index) => ({
              '@type': 'ListItem',
              position: index + 1,
              url: absoluteUrl(`/region/${item.slug}`),
              name: item.name
            }))
          }
        })
      }
    ]
  }
})

onMounted(loadRecommendations)
</script>

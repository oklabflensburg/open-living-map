<template>
  <section>
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Top Empfehlungen</h1>
        <p class="text-sm text-slate-500">
          Auswahl: {{ selectedStateName }}
        </p>
      </div>
      <NuxtLink to="/finder" class="text-sm font-semibold text-blue-700">Gewichte anpassen</NuxtLink>
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

const states = [
  { code: '01', name: 'Schleswig-Holstein' },
  { code: '02', name: 'Hamburg' },
  { code: '03', name: 'Niedersachsen' },
  { code: '04', name: 'Bremen' },
  { code: '05', name: 'Nordrhein-Westfalen' },
  { code: '06', name: 'Hessen' },
  { code: '07', name: 'Rheinland-Pfalz' },
  { code: '08', name: 'Baden-Württemberg' },
  { code: '09', name: 'Bayern' },
  { code: '10', name: 'Saarland' },
  { code: '11', name: 'Berlin' },
  { code: '12', name: 'Brandenburg' },
  { code: '13', name: 'Mecklenburg-Vorpommern' },
  { code: '14', name: 'Sachsen' },
  { code: '15', name: 'Sachsen-Anhalt' },
  { code: '16', name: 'Thüringen' }
]

const selectedStateName = computed(() => {
  if (!store.state_code) {
    return 'Deutschlandweit'
  }
  return states.find((state) => state.code === store.state_code)?.name || 'Unbekanntes Bundesland'
})

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

onMounted(async () => {
  try {
    response.value = await fetchRecommendations({ ...store.$state })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unbekannter Fehler'
  } finally {
    pending.value = false
  }
})
</script>

<template>
  <section>
    <div class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Top Empfehlungen</h1>
        <p class="text-sm text-slate-500">
          Auswahl: {{ selectedStateName }}
        </p>
        <p class="mt-2 text-sm text-slate-600">
          Sortiert nach der Passung zu deinem Suchprofil. Der neutrale Gesamtscore der Gemeinde bleibt separat sichtbar.
        </p>
      </div>
      <div class="w-full max-w-sm space-y-3">
        <StateSelect
          :model-value="currentPreferences.state_code"
          hint="Die Empfehlungen werden nur innerhalb des gewählten Bundeslands berechnet."
          @update:model-value="onStateChange"
        />
        <NuxtLink :to="finderLink" class="inline-block text-sm font-semibold text-blue-700">Gewichte anpassen</NuxtLink>
      </div>
    </div>

    <div class="mb-6">
      <RegionMap :items="data?.response.items || []" :state-boundaries="data?.stateBoundaries || null" :loading="pending" />
    </div>

    <div v-if="pending" class="text-slate-500">Lade Empfehlungen...</div>
    <div v-else-if="error" class="text-red-600">{{ error.message }}</div>
    <div v-else class="grid gap-4 md:grid-cols-2">
      <RegionCard v-for="item in data?.response.items" :key="item.ars" :item="item" />
    </div>
  </section>
</template>

<script setup lang="ts">
import RegionCard from '~/components/RegionCard.vue'
import RegionMap from '~/components/RegionMap.vue'
import StateSelect from '~/components/StateSelect.vue'
import { buildPreferenceQuery, parsePreferenceQuery } from '~/composables/usePreferenceQuery'
import { getGermanStateName } from '~/composables/useGermanStates'
import { usePreferencesStore } from '~/stores/preferences'
import type { GeoJsonFeatureCollection, RecommendationResponse } from '~/types/api'

const { siteName, absoluteUrl } = useSiteSeo()
const store = usePreferencesStore()
const route = useRoute()
const router = useRouter()
const { fetchRecommendations } = useRecommendations()
const { fetchStateBoundaries } = useRegions()

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

const currentPreferences = computed(() => parsePreferenceQuery(route.query, { ...store.$state }))
const selectedStateName = computed(() => getGermanStateName(currentPreferences.value.state_code))
const finderLink = computed(() => ({
  path: '/finder',
  query: buildPreferenceQuery(currentPreferences.value)
}))

watchEffect(() => {
  store.$patch(currentPreferences.value)
})

const requestKey = computed(() => JSON.stringify(buildPreferenceQuery(currentPreferences.value)))

const { data, pending, error } = await useAsyncData<{
  response: RecommendationResponse
  stateBoundaries: GeoJsonFeatureCollection | null
}>(
  () => `results:${requestKey.value}`,
  async () => {
    const preferences = currentPreferences.value
    const [response, stateBoundaries] = await Promise.all([
      fetchRecommendations(preferences),
      fetchStateBoundaries(preferences.state_code)
    ])
    return { response, stateBoundaries }
  },
  {
    watch: [requestKey]
  }
)

async function onStateChange(value: string | null) {
  await router.replace({
    query: buildPreferenceQuery({
      ...currentPreferences.value,
      state_code: value
    })
  })
}

useHead(() => {
  const items = (data.value?.response.items || []).slice(0, 10)
  return {
    link: [{ rel: 'canonical', href: absoluteUrl('/results') }],
    script: [
      {
        key: 'ld-results',
        type: 'application/ld+json',
        innerHTML: JSON.stringify({
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
</script>

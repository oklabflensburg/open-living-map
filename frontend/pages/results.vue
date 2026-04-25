<template>
  <section class="space-y-6">
    <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
      <div class="min-w-0">
        <h1 class="text-2xl font-bold">Top Empfehlungen</h1>
        <p class="text-sm text-slate-500">
          Auswahl: {{ selectedStateName }}
        </p>
        <p class="mt-2 text-sm text-slate-600">
          Sortiert nach der Passung zu deinem Suchprofil. Filter begrenzen die Treffermenge hart, der neutrale
          Gesamtscore der Gemeinde bleibt separat sichtbar.
        </p>
      </div>
      <div class="flex flex-wrap justify-end gap-3 lg:min-w-[34rem]">
        <NuxtLink :to="finderLink" class="inline-flex justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400">
          Gewichte anpassen
        </NuxtLink>
        <ShareButton
          :path="sharePath"
          label="Ergebnisse teilen"
          share-title="Wohnort-Kompass Ergebnisse"
          share-text="Diese Ergebnisliste im Wohnort-Kompass teilen"
        />
      </div>
    </div>

    <div class="flex flex-wrap gap-2">
      <span
        v-for="tag in displayedFilterTags"
        :key="tag"
        class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
      >
        {{ tag }}
      </span>
    </div>

    <details class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <summary class="cursor-pointer text-sm font-semibold text-slate-900">
        Treffermenge filtern
      </summary>
      <div class="mt-4">
        <FinderFilterPanel :model-value="currentPreferences" title="Filter bearbeiten" @update:model-value="onFiltersChange" />
      </div>
    </details>

    <details class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:hidden">
      <summary class="cursor-pointer text-sm font-semibold text-slate-900">
        Karte einblenden
      </summary>
      <div class="mt-4">
        <RegionMap :items="data?.response.items || []" :state-boundaries="data?.stateBoundaries || null" :loading="pending" />
      </div>
    </details>

    <div class="hidden md:block">
      <RegionMap :items="data?.response.items || []" :state-boundaries="data?.stateBoundaries || null" :loading="pending" />
    </div>

    <div v-if="pending" class="rounded-xl border border-slate-200 bg-white p-6 text-slate-500 shadow-sm">Lade Empfehlungen...</div>
    <div v-else-if="error" class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700 shadow-sm">{{ error.message }}</div>
    <div
      v-else-if="!(data?.response.items.length)"
      class="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-700 shadow-sm"
    >
      Für diese Kombination aus Gewichtungen und Filtern wurden keine Orte gefunden. Lockere einzelne Mindestwerte oder
      die Mindestabdeckung, um wieder mehr Treffer zu sehen.
    </div>
    <div v-else class="grid gap-4 md:grid-cols-2">
      <RegionCard
        v-for="(item, index) in data?.response.items"
        :key="item.ars"
        :item="item"
        :profile-preferences="currentPreferences"
        :delta-reference="deltaReference(data.response.items, index)"
        :delta-title="index === 0 ? 'Warum Platz 1?' : 'Unterschied zum vorherigen Rang'"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import FinderFilterPanel from '~/components/FinderFilterPanel.vue'
import RegionCard from '~/components/RegionCard.vue'
import RegionMap from '~/components/RegionMap.vue'
import ShareButton from '~/components/ShareButton.vue'
import {
  activeFilterTags,
  buildPreferenceQuery,
  buildRecommendationPayload,
  parsePreferenceQuery
} from '~/composables/usePreferenceQuery'
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
const sharePath = computed(() => `/results?${new URLSearchParams(buildPreferenceQuery(currentPreferences.value)).toString()}`)
const displayedFilterTags = computed(() => {
  const tags = activeFilterTags(currentPreferences.value, selectedStateName.value)
  return tags.length ? tags : ['Keine harten Filter aktiv']
})

watchEffect(() => {
  store.$patch(currentPreferences.value)
})

const { data, pending, error } = await useAsyncData<{
  response: RecommendationResponse
  stateBoundaries: GeoJsonFeatureCollection | null
}>(
  'results',
  async () => {
    const preferences = currentPreferences.value
    const [response, stateBoundaries] = await Promise.all([
      fetchRecommendations(buildRecommendationPayload(preferences)),
      fetchStateBoundaries(preferences.state_code)
    ])
    return { response, stateBoundaries }
  },
  {
    watch: [() => route.fullPath]
  }
)

async function onFiltersChange(value: typeof currentPreferences.value) {
  store.$patch(value)
  await router.replace({
    query: buildPreferenceQuery(value)
  })
}

function deltaReference(items: RecommendationResponse['items'], index: number) {
  if (!items.length) {
    return null
  }

  if (index === 0) {
    return items[1] || null
  }

  return items[index - 1] || null
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

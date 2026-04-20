<template>
  <section>
    <h1 class="mb-4 text-2xl font-bold">Regionen vergleichen</h1>

    <div class="mb-6 space-y-3">
      <div ref="searchRef" class="relative">
        <div class="flex min-h-[3.25rem] flex-wrap items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 shadow-sm">
          <span
            v-for="region in selectedRegions"
            :key="region.ars"
            class="inline-flex items-center gap-2 rounded-lg bg-sky-100 px-3 py-1 text-sm font-medium text-sky-900"
          >
            <span>{{ region.name }}</span>
            <button
              type="button"
              class="text-sky-700 transition hover:text-sky-900"
              @click="removeRegion(region.ars)"
            >
              ×
            </button>
          </span>

          <input
            v-model="searchQuery"
            type="search"
            placeholder="PLZ, Gemeinde oder AGS hinzufügen, z. B. 24937, Berlin oder 01001000"
            class="min-w-[14rem] flex-1 border-0 bg-transparent px-1 py-1 text-sm text-slate-900 outline-none placeholder:text-slate-400"
            autocomplete="off"
            spellcheck="false"
            @focus="handleSearchFocus"
            @input="openSuggestions = true"
            @keydown.down.prevent="moveSelection(1)"
            @keydown.up.prevent="moveSelection(-1)"
            @keydown.enter.prevent="selectHighlightedResult"
            @keydown.esc="closeSuggestions"
            @keydown.backspace="handleBackspace"
          >
        </div>

        <div
          v-if="openSuggestions"
          class="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-40 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        >
          <div v-if="searchLoading" class="px-4 py-3 text-sm text-slate-500">Lade Orte...</div>
          <div v-else-if="searchError" class="px-4 py-3 text-sm text-rose-600">{{ searchError }}</div>
          <div v-else-if="selectedRegions.length >= 3" class="px-4 py-3 text-sm text-slate-500">
            Maximal drei Regionen können gleichzeitig verglichen werden.
          </div>
          <div v-else-if="searchQuery.trim().length < 2" class="px-4 py-3 text-sm text-slate-500">
            Mindestens 2 Zeichen für PLZ, Gemeinde oder AGS eingeben.
          </div>
          <div v-else-if="!searchResults.length" class="px-4 py-3 text-sm text-slate-500">
            Kein passender Ort gefunden.
          </div>
          <ul v-else class="max-h-80 overflow-y-auto py-2">
            <li v-for="(item, index) in searchResults" :key="item.ars">
              <button
                type="button"
                class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm transition"
                :class="selectedSearchIndex === index ? 'bg-sky-50 text-sky-950' : 'text-slate-700 hover:bg-slate-50'"
                @mouseenter="selectedSearchIndex = index"
                @click="addRegion(item)"
              >
                <span class="min-w-0">
                  <span class="block truncate font-medium">{{ item.name }}</span>
                  <span class="block truncate text-xs text-slate-500">{{ item.state_name }} · AGS {{ item.ars }}</span>
                </span>
                <span class="shrink-0 text-xs font-semibold text-sky-700">Hinzufügen</span>
              </button>
            </li>
          </ul>
        </div>
      </div>

      <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <p class="text-sm text-slate-500">
          Wähle bis zu drei Regionen aus. Der Vergleich aktualisiert sich sofort nach jeder Auswahl.
        </p>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-3">
      <RegionCard v-for="item in items" :key="item.ars" :item="item" :show-profile-context="false" />
    </div>
  </section>
</template>

<script setup lang="ts">
import RegionCard from '~/components/RegionCard.vue'
import type { RecommendationItem, Region } from '~/types/api'

const { siteName, absoluteUrl } = useSiteSeo()
const route = useRoute()
const router = useRouter()
const { fetchCompare } = useRecommendations()
const { searchRegionsAutocomplete } = useRegions()
const compareStore = useCompareStore()

const searchRef = ref<HTMLElement | null>(null)
const searchResults = ref<Region[]>([])
const searchLoading = ref(false)
const searchError = ref('')
const openSuggestions = ref(false)
const selectedSearchIndex = ref(0)
const items = ref<RecommendationItem[]>([])
const compareReady = ref(false)
const suppressNextSuggestionOpen = ref(false)
const searchQuery = computed({
  get: () => compareStore.search_query,
  set: (value: string) => compareStore.setSearchQuery(value)
})
const selectedRegions = computed(() => compareStore.selected_regions)

const title = 'Vergleich'
const description = 'Vergleiche bis zu drei Regionen direkt anhand ihrer Teil-Scores und Datenbasis.'

useSeoMeta({
  title,
  description,
  robots: 'noindex,follow',
  ogUrl: absoluteUrl('/compare'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'website',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl('/compare') }],
  script: [
    {
      key: 'ld-compare',
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: `${title} | ${siteName}`,
        url: absoluteUrl('/compare'),
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
              item: absoluteUrl('/compare')
            }
          ]
        },
        mainEntity: {
          '@type': 'ItemList',
          itemListElement: items.value.map((item, index) => ({
            '@type': 'ListItem',
            position: index + 1,
            url: absoluteUrl(`/region/${item.slug}`),
            name: item.name
          }))
        }
      })
    }
  ]
}))

function recommendationItemToRegion(item: RecommendationItem): Region {
  return {
    ars: item.ars,
    slug: item.slug,
    name: item.name,
    level: item.level,
    state_code: '',
    state_name: item.state_name,
    district_name: item.district_name,
    population: null,
    area_km2: null,
    centroid_lat: item.centroid_lat,
    centroid_lon: item.centroid_lon,
    wikidata_id: null,
    wikidata_url: null,
    wikipedia_url: null
  }
}

async function syncCompareUrl() {
  const ars = selectedRegions.value.map((item) => item.ars).slice(0, 3)
  const nextArs = ars.length ? ars.join(',') : undefined
  const currentArs = typeof route.query.ars === 'string' ? route.query.ars : undefined
  if (nextArs === currentArs) {
    return
  }
  await router.replace({
    query: {
      ...route.query,
      ars: nextArs
    }
  })
}

async function handleSearchFocus() {
  openSuggestions.value = true
}

function closeSuggestions() {
  openSuggestions.value = false
}

function moveSelection(direction: number) {
  if (!openSuggestions.value) {
    openSuggestions.value = true
  }
  if (!searchResults.value.length) {
    return
  }
  const next = selectedSearchIndex.value + direction
  const maxIndex = searchResults.value.length - 1
  selectedSearchIndex.value = next < 0 ? maxIndex : next > maxIndex ? 0 : next
}

function addRegion(region: Region) {
  if (selectedRegions.value.some((item) => item.ars === region.ars) || selectedRegions.value.length >= 3) {
    return
  }
  suppressNextSuggestionOpen.value = true
  compareStore.addRegion(region)
  compareStore.clearSearchQuery()
  selectedSearchIndex.value = 0
  openSuggestions.value = false
}

function removeRegion(ars: string) {
  compareStore.removeRegion(ars)
}

function selectHighlightedResult() {
  const region = searchResults.value[selectedSearchIndex.value] || searchResults.value[0]
  if (!region) {
    return
  }
  addRegion(region)
  closeSuggestions()
}

function handleBackspace() {
  if (searchQuery.value.length === 0 && selectedRegions.value.length) {
    compareStore.popRegion()
  }
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Node)) {
    return
  }
  if (!searchRef.value?.contains(target)) {
    closeSuggestions()
  }
}

async function runCompare() {
  const ars = selectedRegions.value.map((item) => item.ars).slice(0, 3)

  if (!ars.length) {
    items.value = []
    return
  }

  const response = await fetchCompare(ars)
  items.value = response.items
}

watch(searchQuery, () => {
  selectedSearchIndex.value = 0
})

watch(
  () => selectedRegions.value.map((item) => item.ars).join(','),
  async () => {
    await syncCompareUrl()
    if (!compareReady.value) {
      return
    }
    await runCompare()
  }
)

let searchRequestId = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(
  searchQuery,
  (value) => {
    if (suppressNextSuggestionOpen.value) {
      suppressNextSuggestionOpen.value = false
    } else {
      openSuggestions.value = true
    }
    searchError.value = ''

    if (searchTimer) {
      clearTimeout(searchTimer)
    }

    const query = value.trim()
    if (query.length < 2 || selectedRegions.value.length >= 3) {
      searchLoading.value = false
      searchResults.value = []
      return
    }

    searchLoading.value = true
    const selectedArs = new Set(selectedRegions.value.map((item) => item.ars))
    const requestId = ++searchRequestId
    searchTimer = setTimeout(async () => {
      try {
        const response = await searchRegionsAutocomplete(query, 8)
        if (requestId !== searchRequestId) {
          return
        }
        searchResults.value = response.items.filter((item) => !selectedArs.has(item.ars))
      } catch (error) {
        if (requestId !== searchRequestId) {
          return
        }
        searchResults.value = []
        searchError.value = error instanceof Error ? error.message : 'Orte konnten nicht geladen werden.'
      } finally {
        if (requestId === searchRequestId) {
          searchLoading.value = false
        }
      }
    }, 180)
  },
  { flush: 'post' }
)

onMounted(async () => {
  compareStore.hydrate()
  document.addEventListener('click', handleDocumentClick)
  const routeArs = typeof route.query.ars === 'string'
    ? route.query.ars.split(',').map((item) => item.trim()).filter(Boolean).slice(0, 3)
    : []

  if (routeArs.length) {
    const response = await fetchCompare(routeArs)
    items.value = response.items
    compareStore.setSelectedRegions(response.items.map(recommendationItemToRegion))
    compareReady.value = true
    return
  }

  await syncCompareUrl()
  compareReady.value = true
  await runCompare()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
})
</script>

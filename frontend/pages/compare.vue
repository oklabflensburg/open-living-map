<template>
  <section>
    <h1 class="mb-4 text-2xl font-bold">Regionen vergleichen</h1>

    <form class="mb-6 space-y-3" @submit.prevent="runCompare">
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
            placeholder="Ort hinzufügen, z. B. Berlin oder Flensburg"
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
            Mindestens 2 Zeichen eingeben.
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
          Wähle bis zu drei Regionen aus. Die Karten darunter aktualisieren sich nach dem Vergleich.
        </p>
        <button class="rounded-lg bg-blue-700 px-4 py-2 font-semibold text-white transition hover:bg-blue-800" type="submit">
          Vergleichen
        </button>
      </div>
    </form>

    <div class="grid gap-4 md:grid-cols-3">
      <RegionCard v-for="item in items" :key="item.ars" :item="item" />
    </div>
  </section>
</template>

<script setup lang="ts">
import RegionCard from '~/components/RegionCard.vue'
import type { RecommendationItem, Region } from '~/types/api'

const { siteName, absoluteUrl } = useSiteSeo()
const { fetchCompare } = useRecommendations()
const { fetchRegions } = useRegions()

const searchRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const searchOptions = ref<Region[]>([])
const searchLoading = ref(false)
const searchLoaded = ref(false)
const searchError = ref('')
const openSuggestions = ref(false)
const selectedSearchIndex = ref(0)
const selectedRegions = ref<Region[]>([])
const items = ref<RecommendationItem[]>([])
const defaultRegionPrefixes = ['09162', '06412', '05315']

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
      children: JSON.stringify({
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

const searchResults = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('de-DE')
  if (query.length < 2 || selectedRegions.value.length >= 3) {
    return []
  }

  const selectedArs = new Set(selectedRegions.value.map((item) => item.ars))
  return searchOptions.value
    .filter((item) => !selectedArs.has(item.ars))
    .map((item) => {
      const name = item.name.toLocaleLowerCase('de-DE')
      const stateName = item.state_name.toLocaleLowerCase('de-DE')
      let score = 0

      if (name === query) {
        score += 200
      } else if (name.startsWith(query)) {
        score += 120
      } else if (name.includes(query)) {
        score += 80
      }

      if (stateName.startsWith(query)) {
        score += 20
      } else if (stateName.includes(query)) {
        score += 10
      }

      if (item.ars.startsWith(query)) {
        score += 40
      }

      return { item, score }
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score
      }
      return left.item.name.localeCompare(right.item.name, 'de')
    })
    .slice(0, 8)
    .map((entry) => entry.item)
})

async function ensureSearchOptions() {
  if (searchLoaded.value || searchLoading.value) {
    return
  }

  searchLoading.value = true
  searchError.value = ''
  try {
    const response = await fetchRegions()
    searchOptions.value = response.items
    searchLoaded.value = true
  } catch (error) {
    searchError.value = error instanceof Error ? error.message : 'Ortsliste konnte nicht geladen werden.'
  } finally {
    searchLoading.value = false
  }
}

async function handleSearchFocus() {
  openSuggestions.value = true
  await ensureSearchOptions()
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
  selectedRegions.value = [...selectedRegions.value, region]
  searchQuery.value = ''
  selectedSearchIndex.value = 0
  openSuggestions.value = false
}

function removeRegion(ars: string) {
  selectedRegions.value = selectedRegions.value.filter((item) => item.ars !== ars)
}

function selectHighlightedResult() {
  const region = searchResults.value[selectedSearchIndex.value] || searchResults.value[0]
  if (!region) {
    return
  }
  addRegion(region)
}

function handleBackspace() {
  if (searchQuery.value.length === 0 && selectedRegions.value.length) {
    selectedRegions.value = selectedRegions.value.slice(0, -1)
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

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  await ensureSearchOptions()

  if (!selectedRegions.value.length && searchOptions.value.length) {
    selectedRegions.value = defaultRegionPrefixes
      .map((prefix) => searchOptions.value.find((item) => item.ars.startsWith(prefix)))
      .filter((item): item is Region => Boolean(item))
      .slice(0, 3)
  }

  await runCompare()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

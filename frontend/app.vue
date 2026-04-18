<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-blue-50 text-slate-900">
    <header class="border-b border-slate-200 bg-white/70 backdrop-blur">
      <nav class="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <NuxtLink to="/" class="text-lg font-bold tracking-tight">Wohnort-Kompass</NuxtLink>

        <div class="flex w-full flex-col gap-4 lg:w-auto lg:flex-row lg:items-center">
          <div ref="searchRef" class="relative w-full lg:w-[26rem]">
            <input
              v-model="searchQuery"
              type="search"
              placeholder="Ort suchen, z. B. Flensburg oder Oppenau"
              class="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pr-10 text-sm text-slate-900 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
              autocomplete="off"
              spellcheck="false"
              @focus="handleSearchFocus"
              @input="openSuggestions = true"
              @keydown.down.prevent="moveSelection(1)"
              @keydown.up.prevent="moveSelection(-1)"
              @keydown.enter.prevent="openSelectedResult"
              @keydown.esc="closeSuggestions"
            >
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-sky-700"
              @click="openSelectedResult"
            >
              Los
            </button>

            <div
              v-if="openSuggestions"
              class="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-30 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
            >
              <div v-if="searchLoading" class="px-4 py-3 text-sm text-slate-500">Lade Orte...</div>
              <div v-else-if="searchError" class="px-4 py-3 text-sm text-rose-600">{{ searchError }}</div>
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
                    :class="selectedSearchIndex === index ? 'bg-sky-50 text-sky-900' : 'text-slate-700 hover:bg-slate-50'"
                    @mouseenter="selectedSearchIndex = index"
                    @click="openRegion(item.slug)"
                  >
                    <span class="min-w-0">
                      <span class="block truncate font-medium">{{ item.name }}</span>
                      <span class="block truncate text-xs text-slate-500">{{ item.state_name }} · AGS {{ item.ars }}</span>
                    </span>
                    <span class="shrink-0 text-xs font-semibold text-sky-700">Detailseite</span>
                  </button>
                </li>
              </ul>
            </div>
          </div>

          <div class="flex flex-wrap gap-4 text-sm font-medium">
            <NuxtLink to="/finder">Finder</NuxtLink>
            <NuxtLink to="/results">Ranking</NuxtLink>
            <NuxtLink to="/compare">Vergleich</NuxtLink>
            <NuxtLink to="/methodik">Methodik</NuxtLink>
          </div>
        </div>
      </nav>
    </header>
    <main class="mx-auto max-w-6xl px-4 py-8">
      <NuxtPage />
    </main>
    <footer class="mt-10 border-t border-slate-200 bg-white/80">
      <div class="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 text-sm text-slate-600 md:flex-row md:items-center md:justify-between">
        <div>
          <p class="font-medium text-slate-800">{{ siteName }}</p>
          <p>Offene Daten für Regionen in Deutschland.</p>
        </div>
        <div class="flex flex-wrap gap-x-5 gap-y-2">
          <a :href="repoUrl" target="_blank" rel="noreferrer" class="hover:text-sky-700">Repository</a>
          <NuxtLink to="/methodik" class="hover:text-sky-700">Methodik</NuxtLink>
          <NuxtLink to="/impressum" class="hover:text-sky-700">Impressum</NuxtLink>
          <NuxtLink to="/datenschutz" class="hover:text-sky-700">Datenschutz</NuxtLink>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import type { Region } from '~/types/api'

const { siteName, organizationName, siteDescription, siteLocale, absoluteUrl } = useSiteSeo()
const { legal } = useLegalConfig()
const router = useRouter()
const route = useRoute()
const { fetchRegions } = useRegions()
const repoUrl = computed(() => legal.value.repoUrl || 'https://github.com/oklabflensburg/wohnortkompass')

const searchRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const searchOptions = ref<Region[]>([])
const searchLoading = ref(false)
const searchLoaded = ref(false)
const searchError = ref('')
const openSuggestions = ref(false)
const selectedSearchIndex = ref(0)

const searchResults = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('de-DE')
  if (query.length < 2) {
    return []
  }

  const scored = searchOptions.value
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

  return scored.map((entry) => entry.item)
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

function openRegion(slug: string) {
  searchQuery.value = ''
  openSuggestions.value = false
  selectedSearchIndex.value = 0
  router.push(`/region/${slug}`)
}

function openSelectedResult() {
  const first = searchResults.value[selectedSearchIndex.value] || searchResults.value[0]
  if (!first) {
    return
  }
  openRegion(first.slug)
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

watch(searchQuery, () => {
  selectedSearchIndex.value = 0
})

watch(
  () => route.fullPath,
  () => {
    searchQuery.value = ''
    closeSuggestions()
  }
)

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})

useSeoMeta({
  applicationName: siteName,
  description: siteDescription,
  ogSiteName: siteName,
  ogLocale: siteLocale,
  ogImage: absoluteUrl('/og-image.png'),
  ogImageSecureUrl: absoluteUrl('/og-image.png'),
  ogImageAlt: 'Wohnort-Kompass: Regionen in Deutschland mit offenen Daten vergleichen',
  twitterImage: absoluteUrl('/og-image.png'),
  twitterImageAlt: 'Wohnort-Kompass: Regionen in Deutschland mit offenen Daten vergleichen',
  twitterCard: 'summary_large_image'
})

useHead({
  titleTemplate: (titleChunk?: string) => (titleChunk ? `${titleChunk} | ${siteName}` : siteName),
  link: [
    { rel: 'icon', href: '/favicon.ico', sizes: 'any' },
    { rel: 'shortcut icon', href: '/favicon.ico' },
    { rel: 'apple-touch-icon', href: '/favicon.ico' }
  ],
  script: [
    {
      key: 'ld-site',
      type: 'application/ld+json',
      children: JSON.stringify({
        '@context': 'https://schema.org',
        '@graph': [
          {
            '@type': 'WebSite',
            '@id': `${absoluteUrl('/')}#website`,
            name: siteName,
            url: absoluteUrl('/'),
            description: siteDescription,
            inLanguage: 'de',
            potentialAction: {
              '@type': 'SearchAction',
              target: `${absoluteUrl('/results')}?q={search_term_string}`,
              'query-input': 'required name=search_term_string'
            }
          },
          {
            '@type': 'Organization',
            '@id': `${absoluteUrl('/')}#organization`,
            name: organizationName,
            url: absoluteUrl('/'),
            description: siteDescription
          }
        ]
      })
    }
  ]
})
</script>

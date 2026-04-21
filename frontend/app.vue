<template>
  <div class="flex min-h-screen flex-col bg-gradient-to-b from-slate-50 to-blue-50 text-slate-900">

    <header class="sticky top-0 z-[1000] border-b border-white/60 bg-white/75 shadow-[0_10px_30px_rgba(15,23,42,0.06)] backdrop-blur-xl">
      <nav class="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div class="flex items-center justify-between gap-4">
          <NuxtLink to="/" class="group inline-flex items-center gap-3">
            <span class="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-700 text-sm font-black tracking-tight text-white shadow-lg shadow-sky-200">
              WK
            </span>
            <span>
              <span class="block text-lg font-black tracking-tight text-slate-950 transition group-hover:text-sky-700">Wohnort-Kompass</span>
              <span class="block text-xs font-medium text-slate-500">Offene Daten für Regionen in Deutschland</span>
            </span>
          </NuxtLink>

          <button
            type="button"
            class="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-[0_8px_24px_rgba(15,23,42,0.06)] transition hover:bg-slate-50 lg:hidden"
            :aria-expanded="mobileMenuOpen ? 'true' : 'false'"
            aria-controls="mobile-nav"
            aria-label="Navigation öffnen"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <svg v-if="!mobileMenuOpen" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 5a1 1 0 0 1 1-1h12a1 1 0 1 1 0 2H4a1 1 0 0 1-1-1Zm0 5a1 1 0 0 1 1-1h12a1 1 0 1 1 0 2H4a1 1 0 0 1-1-1Zm1 4a1 1 0 1 0 0 2h12a1 1 0 1 0 0-2H4Z" clip-rule="evenodd" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 0 1 1.414 0L10 8.586l4.293-4.293a1 1 0 1 1 1.414 1.414L11.414 10l4.293 4.293a1 1 0 0 1-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 0 1-1.414-1.414L8.586 10 4.293 5.707a1 1 0 0 1 0-1.414Z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <div class="flex w-full flex-col gap-4 lg:w-auto lg:flex-row lg:items-center">
          <div ref="searchRef" class="relative w-full lg:w-[30rem]">
            <input
              v-model="searchQuery"
              type="search"
              placeholder="PLZ, Gemeinde oder AGS suchen, z. B. 24937, Flensburg oder 01001000"
              class="w-full rounded-2xl border border-slate-200/90 bg-white/95 px-4 py-3 pl-12 pr-12 text-sm text-slate-900 shadow-[0_8px_24px_rgba(15,23,42,0.06)] outline-none transition placeholder:text-slate-400 focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
              autocomplete="off"
              spellcheck="false"
              @focus="handleSearchFocus"
              @input="openSuggestions = true"
              @keydown.down.prevent="moveSelection(1)"
              @keydown.up.prevent="moveSelection(-1)"
              @keydown.enter.prevent="openSelectedResult"
              @keydown.esc="closeSuggestions"
            >
            <span class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 3a6 6 0 1 0 3.794 10.648l3.279 3.279a1 1 0 0 0 1.414-1.414l-3.279-3.279A6 6 0 0 0 9 3Zm-4 6a4 4 0 1 1 8 0a4 4 0 0 1-8 0Z" clip-rule="evenodd" />
              </svg>
            </span>
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 rounded-xl bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700 transition hover:bg-sky-100"
              @click="openSelectedResult"
            >
              Los
            </button>

            <div
              v-if="openSuggestions"
              class="absolute left-0 right-0 top-[calc(100%+0.6rem)] z-[120] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.16)]"
            >
              <div v-if="searchLoading" class="px-4 py-3 text-sm text-slate-500">Lade Orte...</div>
              <div v-else-if="searchError" class="px-4 py-3 text-sm text-rose-600">{{ searchError }}</div>
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

          <div
            id="mobile-nav"
            class="rounded-2xl border border-slate-200/80 bg-white/80 p-1.5 shadow-[0_8px_24px_rgba(15,23,42,0.05)]"
            :class="mobileMenuOpen ? 'block' : 'hidden lg:block'"
          >
            <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:overflow-x-auto">
            <NuxtLink
              v-for="item in navItems"
              :key="item.activePath"
              :to="item.to"
              class="whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold transition"
              :class="navLinkClass(item.activePath)"
              @click="mobileMenuOpen = false"
            >
              {{ item.label }}
            </NuxtLink>
            </div>
          </div>
        </div>
      </nav>
    </header>

    <main class="relative z-0 mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <NuxtPage />
    </main>

    <footer class="mt-10 border-t border-white/60 bg-white/70 backdrop-blur-xl">
      <div class="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 md:grid-cols-[1.2fr_1fr_1fr] lg:px-8">
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <span class="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-700 text-xs font-black text-white">WK</span>
            <div>
              <p class="font-semibold text-slate-900">{{ siteName }}</p>
              <p class="text-sm text-slate-600">Offene Daten für Regionen in Deutschland.</p>
            </div>
          </div>
          <p class="max-w-md text-sm leading-6 text-slate-600">
            Wohnort-Kompass bündelt Klima, Luftqualität, Demografie, Alltagsnähe, Verkehrssicherheit und ÖPNV in einer
            nachvollziehbaren, datenbasierten Vergleichsansicht.
          </p>
        </div>

        <div>
          <p class="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Navigation</p>
          <div class="mt-3 flex flex-col gap-2 text-sm">
            <NuxtLink v-for="item in navItems" :key="`footer-${item.activePath}`" :to="item.to" class="text-slate-700 transition hover:text-sky-700">
              {{ item.label }}
            </NuxtLink>
          </div>
        </div>

        <div>
          <p class="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Recht & Projekt</p>
          <div class="mt-3 flex flex-col gap-2 text-sm">
            <a :href="repoUrl" target="_blank" rel="noreferrer" class="text-slate-700 transition hover:text-sky-700">Repository</a>
            <NuxtLink to="/impressum" class="text-slate-700 transition hover:text-sky-700">Impressum</NuxtLink>
            <NuxtLink to="/datenschutz" class="text-slate-700 transition hover:text-sky-700">Datenschutz</NuxtLink>
            <NuxtLink to="/methodik" class="text-slate-700 transition hover:text-sky-700">Datenquellen & Methodik</NuxtLink>
          </div>
        </div>
      </div>

      <div class="border-t border-slate-200/80">
        <div class="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-4 text-xs text-slate-500 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <p>© {{ new Date().getFullYear() }} {{ siteName }}</p>
          <p>Gebaut mit Nuxt, FastAPI, PostGIS und offenen Datenquellen.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { buildPreferenceQuery } from '~/composables/usePreferenceQuery'
import type { Region } from '~/types/api'
import { usePreferencesStore } from '~/stores/preferences'

const { siteName, organizationName, siteDescription, siteLocale, absoluteUrl } = useSiteSeo()
const { legal } = useLegalConfig()
const router = useRouter()
const route = useRoute()
const preferencesStore = usePreferencesStore()
const { searchRegionsAutocomplete } = useRegions()
const repoUrl = computed(() => legal.value.repoUrl || 'https://github.com/oklabflensburg/wohnortkompass')
const navItems = computed(() => [
  {
    to: {
      path: '/finder',
      query: buildPreferenceQuery({ ...preferencesStore.$state })
    },
    activePath: '/finder',
    label: 'Finder'
  },
  { to: '/results', activePath: '/results', label: 'Ranking' },
  { to: '/compare', activePath: '/compare', label: 'Vergleich' },
  { to: '/methodik', activePath: '/methodik', label: 'Methodik' }
])

const searchRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const searchResults = ref<Region[]>([])
const searchLoading = ref(false)
const searchError = ref('')
const openSuggestions = ref(false)
const selectedSearchIndex = ref(0)
const mobileMenuOpen = ref(false)

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

function openRegion(slug: string) {
  searchQuery.value = ''
  openSuggestions.value = false
  mobileMenuOpen.value = false
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

function navLinkClass(path: string) {
  const active = route.path === path
  return active
    ? 'bg-slate-900 text-white shadow-sm'
    : 'text-slate-700 hover:bg-slate-100 hover:text-slate-950'
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
  () => route.path,
  () => {
    mobileMenuOpen.value = false
  }
)

let searchRequestId = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(
  searchQuery,
  (value) => {
    openSuggestions.value = true
    searchError.value = ''

    if (searchTimer) {
      clearTimeout(searchTimer)
    }

    const query = value.trim()
    if (query.length < 2) {
      searchLoading.value = false
      searchResults.value = []
      return
    }

    searchLoading.value = true
    const requestId = ++searchRequestId
    searchTimer = setTimeout(async () => {
      try {
        const response = await searchRegionsAutocomplete(query, 8)
        if (requestId !== searchRequestId) {
          return
        }
        searchResults.value = response.items
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
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
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
      innerHTML: JSON.stringify({
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

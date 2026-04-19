<template>
  <section class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-2">
        <p class="inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide" :class="categoryMeta.badgeClass">
          Top 100
        </p>
        <h1 class="text-3xl font-black tracking-tight text-slate-900">
          {{ categoryMeta.label }} in {{ scopeName }}
        </h1>
        <p class="max-w-3xl text-sm text-slate-600">
          {{ introText }}
        </p>
      </div>

      <div class="flex flex-wrap gap-3">
        <NuxtLink to="/finder" active-class="" exact-active-class="" class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-400">
          Eigene Gewichtung
        </NuxtLink>
        <NuxtLink to="/" active-class="" exact-active-class="" class="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">
          Alle Toplisten
        </NuxtLink>
      </div>
    </div>

    <div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" :class="categoryMeta.cardClass">
      <div class="grid gap-3 text-sm text-slate-700 md:grid-cols-3">
        <p>
          <span class="font-semibold text-slate-900">Gebiet:</span>
          {{ scopeName }}
        </p>
        <p>
          <span class="font-semibold text-slate-900">Kategorie:</span>
          {{ categoryMeta.label }}
        </p>
        <p>
          <span class="font-semibold text-slate-900">Einträge:</span>
          {{ response?.items.length || 0 }}
        </p>
      </div>
    </div>

    <div v-if="pending" class="rounded-xl border border-slate-200 bg-white p-6 text-slate-500 shadow-sm">
      Lade Top-100-Liste...
    </div>
    <div v-else-if="errorMessage" class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700 shadow-sm">
      {{ errorMessage }}
    </div>
    <div v-else class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-4 py-3">Rang</th>
              <th class="px-4 py-3">Region</th>
              <th class="px-4 py-3 text-right">{{ categoryMeta.label }}</th>
              <th class="px-4 py-3 text-right">Gesamtscore</th>
              <th class="px-4 py-3 text-right">Aktion</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="(item, index) in response?.items || []" :key="item.ars" class="hover:bg-slate-50/80">
              <td class="px-4 py-3 font-semibold text-slate-900">{{ index + 1 }}</td>
              <td class="px-4 py-3">
                <div class="font-medium text-slate-900">{{ item.name }}</div>
                <div class="text-xs text-slate-500">{{ locationSubtitle(item) }}</div>
              </td>
              <td class="px-4 py-3 text-right font-semibold text-slate-900">{{ getRankingScore(item, category).toFixed(1) }}</td>
              <td class="px-4 py-3 text-right text-slate-600">{{ item.score_total.toFixed(1) }}</td>
              <td class="px-4 py-3 text-right">
                <NuxtLink :to="`/region/${item.slug}`" class="font-semibold text-blue-700 hover:text-blue-800">
                  Details
                </NuxtLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { buildTopRankingPath, getRankingCategory, getRankingScore, type RankingCategory } from '~/composables/useRankingCategories'
import {
  germanyRankingScope,
  getGermanStateByCode,
  getGermanStateBySlug
} from '~/composables/useGermanStates'
import type { RecommendationResponse } from '~/types/api'

const route = useRoute()
const { siteName, absoluteUrl } = useSiteSeo()
const { fetchTopRankings } = useRecommendations()

const stateSlug = String(route.params.stateCode || '')
const category = String(route.params.category || '') as RankingCategory

const categoryMeta = getRankingCategory(category)
const stateMeta = getGermanStateBySlug(stateSlug) || getGermanStateByCode(stateSlug)
const isNationwide = stateSlug === germanyRankingScope.slug

if (!categoryMeta || (!stateMeta && !isNationwide)) {
  throw createError({ statusCode: 404, statusMessage: 'Topliste nicht gefunden' })
}

const scopeName = stateMeta?.name || germanyRankingScope.name
const scopeCode = stateMeta?.code || null
const canonicalScopeSlug = stateMeta?.slug || germanyRankingScope.slug
const title = `Top 100 ${categoryMeta.label} in ${scopeName}`
const categoryExplanation = category === 'landuse'
  ? 'Im Flächennutzungs-Score stecken amtliche Flächenatlas-Kennzahlen zur Flächennutzung.'
  : `${categoryMeta.label} basiert auf den zugehörigen Indikatoren dieser Kategorie.`
const description = isNationwide
  ? `Top 100 Gemeinden in Deutschland, sortiert nach ${categoryMeta.label}. ${categoryExplanation}`
  : `Top 100 Gemeinden in ${scopeName}, sortiert nach ${categoryMeta.label}. ${categoryExplanation}`
const introText = isNationwide
  ? `Die Liste sortiert alle verfügbaren Gemeinden in Deutschland nach dem Kategorie-Score ${categoryMeta.label.toLowerCase()}. ${categoryExplanation}`
  : `Die Liste sortiert alle verfügbaren Gemeinden im gewählten Bundesland nach dem Kategorie-Score ${categoryMeta.label.toLowerCase()}. ${categoryExplanation}`

useSeoMeta({
  title,
  description,
  ogUrl: absoluteUrl(buildTopRankingPath(canonicalScopeSlug, category)),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'website',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl(buildTopRankingPath(canonicalScopeSlug, category)) }],
  script: [
    {
      key: `ld-top-100-${canonicalScopeSlug}-${category}`,
      type: 'application/ld+json',
      children: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: `${title} | ${siteName}`,
        url: absoluteUrl(buildTopRankingPath(canonicalScopeSlug, category)),
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
              name: `${categoryMeta.label} ${scopeName}`,
              item: absoluteUrl(buildTopRankingPath(canonicalScopeSlug, category))
            }
          ]
        }
      })
    }
  ]
}))

const pending = ref(true)
const errorMessage = ref('')
const response = ref<RecommendationResponse | null>(null)

function levelLabel(level: string) {
  if (level === 'kreisfreie_stadt') {
    return 'Kreisfreie Stadt'
  }
  if (level === 'landkreis' || level === 'kreis') {
    return 'Landkreis'
  }
  if (level === 'gemeinde') {
    return 'Gemeinde'
  }
  return 'Region'
}

function locationSubtitle(item: RecommendationResponse['items'][number]) {
  if (item.level === 'gemeinde' && item.district_name) {
    return `AGS ${item.ars} · ${item.state_name} · ${item.district_name}`
  }
  return `AGS ${item.ars} · ${item.state_name} · ${levelLabel(item.level)}`
}

try {
  response.value = await fetchTopRankings(category, scopeCode, 100)
} catch (error) {
  errorMessage.value = error instanceof Error ? error.message : 'Die Topliste konnte nicht geladen werden.'
} finally {
  pending.value = false
}
</script>

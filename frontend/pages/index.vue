<template>
  <section class="space-y-10">
    <div class="grid gap-8 md:grid-cols-2 md:items-center">
      <div>
        <p class="mb-2 inline-block rounded bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
          MVP Deutschland
        </p>
        <h1 class="text-4xl font-black tracking-tight text-slate-900">
          Finde passende Gemeinden und Orte für deinen Alltag.
        </h1>
        <p class="mt-4 text-slate-600">
          Wohnort-Kompass kombiniert offene Daten aus Klima, Luft, Verkehrssicherheit, Demografie, Alltagsnähe, Flächennutzung und ÖPNV.
        </p>
        <div class="mt-6 flex gap-3">
          <NuxtLink to="/finder" class="rounded bg-blue-700 px-5 py-3 font-semibold text-white hover:bg-blue-800">Jetzt starten</NuxtLink>
          <NuxtLink to="/methodik" class="rounded border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700">Methodik</NuxtLink>
        </div>
      </div>
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold">Was du bekommst</h2>
        <ul class="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-700">
          <li>Top-Ranking basierend auf deinen Gewichtungen</li>
          <li>Teil-Scores je Gemeinde mit nachvollziehbarer Begründung</li>
          <li>Vergleich von bis zu 3 Gemeinden</li>
        </ul>
      </div>
    </div>

    <section class="space-y-5">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Toplisten</p>
          <h2 class="text-2xl font-black tracking-tight text-slate-900">Top 100 für Deutschland und pro Bundesland</h2>
        </div>
        <p class="max-w-2xl text-sm text-slate-600">
          Direkte Listen für Deutschland gesamt und für jede Kombination aus Bundesland und Teil-Score.
        </p>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="scope in rankingScopes" :key="scope.slug" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between gap-3">
            <h3 class="text-lg font-semibold text-slate-900">{{ scope.name }}</h3>
            <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{{ scope.code || 'DE' }}</span>
          </div>

          <div class="grid gap-2 sm:grid-cols-2">
            <NuxtLink
              v-for="category in rankingCategories"
              :key="`${scope.slug}-${category.key}`"
              :to="buildTopRankingPath(scope.slug, category.key)"
              class="rounded-xl border px-3 py-2 text-sm font-medium text-slate-700 transition hover:-translate-y-0.5 hover:text-slate-900"
              :class="category.cardClass"
            >
              {{ category.label }}
            </NuxtLink>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { buildTopRankingPath, rankingCategories } from '~/composables/useRankingCategories'
import { germanStates, germanyRankingScope } from '~/composables/useGermanStates'

const rankingScopes = [germanyRankingScope, ...germanStates]

const { siteName, siteDescription, absoluteUrl } = useSiteSeo()

const title = 'Wohnort finden mit offenen Daten'
const description =
  'Vergleiche Gemeinden in Deutschland nach Klima, Luftqualität, Verkehrssicherheit, Demografie, Alltagsnähe, Flächennutzung und ÖPNV.'

useSeoMeta({
  title,
  description,
  ogUrl: absoluteUrl('/'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'website',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary_large_image'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl('/') }],
  script: [
    {
      key: 'ld-home',
      type: 'application/ld+json',
      children: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        name: `${title} | ${siteName}`,
        url: absoluteUrl('/'),
        description,
        breadcrumb: {
          '@type': 'BreadcrumbList',
          itemListElement: [
            {
              '@type': 'ListItem',
              position: 1,
              name: 'Startseite',
              item: absoluteUrl('/')
            }
          ]
        },
        isPartOf: {
          '@id': `${absoluteUrl('/')}#website`
        }
      })
    }
  ]
}))
</script>

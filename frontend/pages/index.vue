<template>
  <section class="grid gap-8 md:grid-cols-2 md:items-center">
    <div>
      <p class="mb-2 inline-block rounded bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
        MVP Deutschland
      </p>
      <h1 class="text-4xl font-black tracking-tight text-slate-900">
        Finde passende Kreise und kreisfreie Städte für deinen Alltag.
      </h1>
      <p class="mt-4 text-slate-600">
        Wohnort-Kompass kombiniert offene Daten aus Klima, Luft, Sicherheit, Demografie, Alltagsnähe und ÖPNV.
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
        <li>Regionale Teil-Scores mit nachvollziehbarer Begründung</li>
        <li>Vergleich von bis zu 3 Regionen</li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
const { siteName, siteDescription, absoluteUrl } = useSiteSeo()

const title = 'Wohnort finden mit offenen Daten'
const description =
  'Vergleiche Kreise und kreisfreie Städte in Deutschland nach Klima, Luftqualität, Sicherheit, Demografie, Alltagsnähe und ÖPNV.'

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

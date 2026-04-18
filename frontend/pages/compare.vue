<template>
  <section>
    <h1 class="mb-4 text-2xl font-bold">Regionen vergleichen</h1>

    <form class="mb-6 flex flex-col gap-3 md:flex-row" @submit.prevent="runCompare">
      <input
        v-model="arsInput"
        type="text"
        placeholder="z.B. 09162,06412,05315"
        class="w-full rounded border border-slate-300 px-3 py-2"
      >
      <button class="rounded bg-blue-700 px-4 py-2 font-semibold text-white">Vergleichen</button>
    </form>

    <div class="grid gap-4 md:grid-cols-3">
      <RegionCard v-for="item in items" :key="item.ars" :item="item" />
    </div>
  </section>
</template>

<script setup lang="ts">
import RegionCard from '~/components/RegionCard.vue'
import type { RecommendationItem } from '~/types/api'

const { siteName, absoluteUrl } = useSiteSeo()
const { fetchCompare } = useRecommendations()

const arsInput = ref('09162,06412,05315')
const items = ref<RecommendationItem[]>([])

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

async function runCompare() {
  const ars = arsInput.value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 3)

  if (!ars.length) {
    items.value = []
    return
  }

  const response = await fetchCompare(ars)
  items.value = response.items
}

onMounted(runCompare)
</script>

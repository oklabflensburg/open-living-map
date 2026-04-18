<template>
  <section class="mx-auto max-w-3xl space-y-6">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h1 class="text-2xl font-bold">Impressum</h1>
      <p class="mt-3 text-sm text-slate-700">
        Verantwortlich für dieses Online-Angebot ist die nachfolgend genannte Person.
        Die Angaben dienen der Anbieterkennzeichnung und Kontaktaufnahme.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Angaben gemäß § 5 TMG</h2>
      <div class="mt-4 space-y-1 text-sm text-slate-700">
        <p class="font-medium text-slate-900">{{ legal.name || 'Bitte NUXT_PUBLIC_LEGAL_NAME setzen' }}</p>
        <p v-if="legal.representative">Vertreten durch: {{ legal.representative }}</p>
        <p v-if="legal.street">{{ legal.street }}</p>
        <p v-if="postalLine">{{ postalLine }}</p>
        <p v-if="legal.country">{{ legal.country }}</p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Kontakt</h2>
      <div class="mt-4 space-y-1 text-sm text-slate-700">
        <p v-if="legal.email">
          E-Mail:
          <a :href="`mailto:${legal.email}`" class="text-sky-700 underline">{{ legal.email }}</a>
        </p>
        <p v-if="legal.phone">Telefon: {{ legal.phone }}</p>
      </div>
    </div>

    <div v-if="legal.vatId" class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Umsatzsteuer-ID</h2>
      <p class="mt-4 text-sm text-slate-700">{{ legal.vatId }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
const { siteName, absoluteUrl } = useSiteSeo()
const { legal, postalLine } = useLegalConfig()

const title = 'Impressum'
const description = 'Rechtliche Anbieterkennzeichnung von Wohnort-Kompass.'

useSeoMeta({
  title,
  description,
  ogUrl: absoluteUrl('/impressum'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'article',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl('/impressum') }],
  script: [
    {
      key: 'ld-impressum',
      type: 'application/ld+json',
      children: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        name: `${title} | ${siteName}`,
        url: absoluteUrl('/impressum'),
        description
      })
    }
  ]
}))
</script>

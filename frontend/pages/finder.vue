<template>
  <section class="mx-auto max-w-7xl space-y-6">
    <div class="space-y-2">
      <h1 class="text-2xl font-bold">Gewichtungen festlegen</h1>
      <p class="max-w-3xl text-sm text-slate-600">
        Lege fest, welche Themen für dich wichtig sind. Die linke Spalte steuert die Gewichtung, die rechte Spalte
        zeigt direkt, wie der Score zusammengesetzt ist und welche Kennzahlen dahinterstehen.
      </p>
    </div>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)] xl:items-start">
      <div class="xl:sticky xl:top-28">
        <PreferenceForm v-model="form" @submit="submit" />
      </div>

      <div class="space-y-6">
        <div class="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 class="text-lg font-semibold">So wird dein Score berechnet</h2>
          <p class="text-sm text-slate-700">
            Jede Kategorie hat einen Teil-Score von 0 bis 100. Diese Teil-Scores werden mit deinen Gewichten (0 bis 5)
            kombiniert. Wenn alle Gewichte 0 sind, ist der Gesamtscore 0.
          </p>

          <div class="rounded bg-slate-50 p-3 text-xs text-slate-700">
            <p class="font-semibold">Formel</p>
            <p>
              Gesamt = (Klima×{{ form.climate_weight }} + Luft×{{ form.air_weight }} + Sicherheit×{{ form.safety_weight
              }} + Demografie×{{ form.demographics_weight }} + Alltagsnähe×{{ form.amenities_weight }} + Flächennutzung×{{ form.landuse_weight }} + ÖPNV×{{
                form.oepnv_weight
              }}) / {{ weightSum }}
            </p>
          </div>

          <div class="text-xs text-slate-600">
            Effektive Anteile:
            Klima {{ effectiveWeights.climate }}% ·
            Luft {{ effectiveWeights.air }}% ·
            Sicherheit {{ effectiveWeights.safety }}% ·
            Demografie {{ effectiveWeights.demographics }}% ·
            Alltagsnähe {{ effectiveWeights.amenities }}% ·
            Flächennutzung {{ effectiveWeights.landuse }}% ·
            ÖPNV {{ effectiveWeights.oepnv }}%
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 class="text-lg font-semibold">Worauf du beim Ranking achten solltest</h2>
          <div class="mt-3 space-y-3 text-sm text-slate-700">
            <p>
              Der Finder berechnet keinen neutralen Amtsscore, sondern eine personalisierte
              <span class="font-semibold text-slate-900">Passung zu deinem Suchprofil</span>.
              Hohe Gewichte verschieben das Ranking bewusst in Richtung der von dir priorisierten Kategorien.
            </p>
            <p>
              Kategorien mit unvollständiger Datenabdeckung fließen später nicht blind als `0` ein. Stattdessen werden
              nur Kategorien mit vorhandener Datenbasis für den Profilscore berücksichtigt.
            </p>
            <p>
              Einige Daten beruhen auf
              <span class="font-semibold text-slate-900">Proxy- oder Stationszuordnungen</span>,
              zum Beispiel Klima- oder Luftwerte aus der nächstgelegenen Messstation. Diese Hinweise siehst du später
              in den Ergebnis- und Detailansichten transparent ausgewiesen.
            </p>
          </div>

          <div class="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Aktuell am stärksten gewichtet</p>
            <p class="mt-2 text-sm text-slate-800">
              {{ rankingFocusText }}
            </p>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 class="mb-4 text-lg font-semibold">Welche Werte dahinterstehen</h2>
          <div class="grid gap-4 md:grid-cols-2">
            <article
              v-for="item in categoryDetails"
              :key="item.key"
              class="rounded-xl border p-4 shadow-sm"
              :class="item.cardClass"
            >
              <p class="text-xs font-semibold uppercase tracking-wide" :class="item.kickerClass">{{ item.kicker }}</p>
              <h3 class="mt-2 font-semibold text-slate-900">{{ item.title }}</h3>
              <p class="mt-1 text-sm text-slate-700">{{ item.description }}</p>
              <p class="mt-3 text-xs font-medium text-slate-500">Enthaltene Kennzahlen</p>
              <p class="mt-1 text-sm text-slate-700">{{ item.indicators.join(', ') }}</p>
              <p class="mt-3 text-xs font-medium text-slate-500">Bewertungslogik</p>
              <p class="mt-1 text-sm text-slate-700">{{ item.direction }}</p>
            </article>
          </div>

          <p class="mt-4 text-xs text-slate-500">
            Hinweis: Alle Indikatoren werden auf 0 bis 100 normiert. Danach wird pro Kategorie gemittelt und anschließend
            mit deinen Gewichten verrechnet.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import PreferenceForm from '~/components/PreferenceForm.vue'
import { buildPreferenceQuery, parsePreferenceQuery, preferenceQueryEquals } from '~/composables/usePreferenceQuery'
import { usePreferencesStore } from '~/stores/preferences'

const { siteName, absoluteUrl } = useSiteSeo()
const store = usePreferencesStore()
const route = useRoute()
const router = useRouter()
const initialPreferences = parsePreferenceQuery(route.query, { ...store.$state })
store.$patch(initialPreferences)
const form = ref({ ...initialPreferences })

const title = 'Finder'
const description =
  'Lege Gewichtungen für Klima, Luftqualität, Verkehrssicherheit, Demografie, Alltagsnähe, Flächennutzung und ÖPNV fest und berechne daraus passende Regionen.'

useSeoMeta({
  title,
  description,
  ogUrl: absoluteUrl('/finder'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'website',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl('/finder') }],
  script: [
    {
      key: 'ld-finder',
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        name: `${title} | ${siteName}`,
        url: absoluteUrl('/finder'),
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
              item: absoluteUrl('/finder')
            }
          ]
        }
      })
    }
  ]
}))

const weightSum = computed(() => {
  const sum =
    form.value.climate_weight +
    form.value.air_weight +
    form.value.safety_weight +
    form.value.demographics_weight +
    form.value.amenities_weight +
    form.value.landuse_weight +
    form.value.oepnv_weight
  return sum === 0 ? 1 : sum
})

const effectiveWeights = computed(() => {
  const sum =
    form.value.climate_weight +
    form.value.air_weight +
    form.value.safety_weight +
    form.value.demographics_weight +
    form.value.amenities_weight +
    form.value.landuse_weight +
    form.value.oepnv_weight
  if (sum === 0) {
    return { climate: 0, air: 0, safety: 0, demographics: 0, amenities: 0, landuse: 0, oepnv: 0 }
  }
  return {
    climate: Math.round((form.value.climate_weight / sum) * 100),
    air: Math.round((form.value.air_weight / sum) * 100),
    safety: Math.round((form.value.safety_weight / sum) * 100),
    demographics: Math.round((form.value.demographics_weight / sum) * 100),
    amenities: Math.round((form.value.amenities_weight / sum) * 100),
    landuse: Math.round((form.value.landuse_weight / sum) * 100),
    oepnv: Math.round((form.value.oepnv_weight / sum) * 100)
  }
})

const rankingFocusText = computed(() => {
  const weighted = [
    { label: 'Klima', weight: form.value.climate_weight },
    { label: 'Luftqualität', weight: form.value.air_weight },
    { label: 'Verkehrssicherheit', weight: form.value.safety_weight },
    { label: 'Demografie/Familie', weight: form.value.demographics_weight },
    { label: 'Alltagsnähe', weight: form.value.amenities_weight },
    { label: 'Flächennutzung', weight: form.value.landuse_weight },
    { label: 'ÖPNV', weight: form.value.oepnv_weight }
  ].filter((entry) => entry.weight > 0)

  if (!weighted.length) {
    return 'Noch keine Kategorie gewichtet. Mit allen Gewichten auf 0 ergibt sich konsequent kein Profilscore.'
  }

  const maxWeight = Math.max(...weighted.map((entry) => entry.weight))
  const leaders = weighted
    .filter((entry) => entry.weight === maxWeight)
    .map((entry) => entry.label)

  if (leaders.length === 1) {
    return `${leaders[0]} dominiert aktuell dein Suchprofil. Regionen mit hoher Ausprägung in dieser Kategorie steigen im Ranking deutlich.`
  }

  if (leaders.length === 2) {
    return `${leaders[0]} und ${leaders[1]} dominieren aktuell dein Suchprofil. Das Ranking sucht deshalb nach Regionen, die beide Schwerpunkte zugleich gut abdecken.`
  }

  return 'Mehrere Kategorien sind aktuell gleich stark gewichtet. Das Ranking bleibt dadurch breiter und weniger auf einen einzelnen Schwerpunkt zugespitzt.'
})

const categoryDetails = [
  {
    key: 'climate',
    kicker: 'Kategorie',
    kickerClass: 'text-amber-700',
    cardClass: 'border-amber-200 bg-amber-50/70',
    title: 'Klima',
    description: 'Klimatische Belastung und Niederschlag auf Basis von DWD-Daten.',
    indicators: ['Hitzetage', 'Sommertage', 'Niederschlag'],
    direction: 'Weniger Hitzetage sind besser. Die übrigen Klimaindikatoren werden je nach fachlicher Richtung bewertet.'
  },
  {
    key: 'air',
    kicker: 'Kategorie',
    kickerClass: 'text-sky-700',
    cardClass: 'border-sky-200 bg-sky-50/70',
    title: 'Luftqualität',
    description: 'Luftschadstoffe aus UBA-Stationen, auf Kreise aggregiert.',
    indicators: ['Stickstoffdioxid (NO₂)', 'Feinstaub PM10', 'Feinstaub PM2.5'],
    direction: 'Niedriger ist besser.'
  },
  {
    key: 'safety',
    kicker: 'Kategorie',
    kickerClass: 'text-rose-700',
    cardClass: 'border-rose-200 bg-rose-50/70',
    title: 'Verkehrssicherheit',
    description: 'Unfallatlas-Unfallorte pro Kreis (Destatis).',
    indicators: ['Verkehrsunfälle gesamt'],
    direction: 'Niedriger ist besser.'
  },
  {
    key: 'demographics',
    kicker: 'Kategorie',
    kickerClass: 'text-violet-700',
    cardClass: 'border-violet-200 bg-violet-50/70',
    title: 'Demografie/Familie',
    description: 'Kreisindikatoren aus GENESIS (Bevölkerung, Altersstruktur, Geschlechteranteil).',
    indicators: ['Einwohner gesamt', 'Frauenanteil', 'Anteil unter 18 Jahren', 'Anteil ab 65 Jahren'],
    direction: 'Die Richtung hängt von der jeweiligen Kennzahl ab; nicht alle demografischen Werte werden gleich interpretiert.'
  },
  {
    key: 'amenities',
    kicker: 'Kategorie',
    kickerClass: 'text-emerald-700',
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    title: 'Alltagsnähe',
    description: 'POI-Dichte aus OSM je Kreis.',
    indicators: ['Dichte alltagsrelevanter Einrichtungen'],
    direction: 'Höher ist besser.'
  },
  {
    key: 'landuse',
    kicker: 'Kategorie',
    kickerClass: 'text-orange-700',
    cardClass: 'border-orange-200 bg-orange-50/70',
    title: 'Flächennutzung',
    description: 'Amtliche Flächenstatistik aus dem Flächenatlas auf Gemeindeebene.',
    indicators: [
      'Waldanteil',
      'Landwirtschaftsanteil',
      'Siedlungs- und Verkehrsflächenanteil',
      'Verkehrsflächenanteil',
      'Siedlungs- und Verkehrsfläche je Einwohner'
    ],
    direction: 'Mehr Wald- und Landwirtschaftsfläche wirkt positiv. Hohe Verkehrs- und Siedlungsflächenanteile wirken negativ.'
  },
  {
    key: 'oepnv',
    kicker: 'Kategorie',
    kickerClass: 'text-indigo-700',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    title: 'ÖPNV',
    description: 'ÖPNV-Haltestellen, Abfahrtsdichte und Regelmäßigkeit aus GTFS.',
    indicators: ['Haltestellendichte', 'Abfahrten je 10.000 Einwohner', 'Regelmäßigkeit des Angebots'],
    direction: 'Höher ist besser.'
  }
]

function submit() {
  store.$patch(form.value)
  router.push({
    path: '/results',
    query: buildPreferenceQuery(form.value)
  })
}

watch(
  form,
  async (value) => {
    store.$patch(value)

    if (preferenceQueryEquals(route.query, value)) {
      return
    }

    await router.replace({
      query: buildPreferenceQuery(value)
    })
  },
  { deep: true }
)
</script>

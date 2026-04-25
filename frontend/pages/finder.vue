<template>
  <section class="mx-auto max-w-7xl space-y-6">
    <div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Finder</p>
      <h1 class="mt-2 text-2xl font-bold text-slate-950 sm:text-3xl">Suchprofil für deinen Wohnort einstellen</h1>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
        Wähle ein Profil, passe Gewichte an und begrenze die Treffermenge mit harten Filtern.
        Links siehst du sofort, welche Kriterien dein Ranking gerade prägen.
      </p>
    </div>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(22rem,0.85fr)] xl:items-start">
      <div class="order-first space-y-4 xl:order-last xl:sticky xl:top-28">
        <PreferenceForm v-model="form" @submit="submit" />
        <FinderFilterPanel v-model="form" title="Filter setzen" />
      </div>

      <div class="space-y-6">
        <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-100 p-5 sm:p-6" :class="activePresetPanelClass">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Aktuelles Suchprofil</p>
                <h2 class="mt-2 text-xl font-bold text-slate-950">{{ activePresetTitle }}</h2>
                <p class="mt-1 max-w-2xl text-sm leading-6 text-slate-600">{{ activePresetDescription }}</p>
              </div>
              <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="activePresetBadgeClass">
                {{ selectedStateText }}
              </span>
            </div>
          </div>

          <div class="p-5 sm:p-6">
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-semibold text-slate-900">Stärkste Treiber</h3>
                <div class="mt-3 grid gap-3 sm:grid-cols-3">
                  <article
                    v-for="entry in topWeightedCategories"
                    :key="entry.label"
                    class="rounded-xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ entry.label }}</p>
                    <p class="mt-2 text-2xl font-bold text-slate-950">{{ entry.weight }}/5</p>
                    <p class="mt-1 text-xs text-slate-500">{{ entry.share }} % Anteil</p>
                  </article>
                </div>
              </div>

              <div class="space-y-2">
                <div
                  v-for="entry in allWeightBars"
                  :key="entry.key"
                  class="grid grid-cols-[8rem_minmax(0,1fr)_3rem] items-center gap-3 text-sm"
                >
                  <span class="truncate font-medium text-slate-700">{{ entry.label }}</span>
                  <span class="h-2 rounded-full bg-slate-100">
                    <span class="block h-2 rounded-full" :class="entry.barClass" :style="{ width: `${entry.share}%` }" />
                  </span>
                  <span class="text-right text-xs font-semibold text-slate-500">{{ entry.share }}%</span>
                </div>
              </div>
            </div>
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
            <p class="mt-3 text-xs text-slate-600">
              Filter: {{ currentFilterText }}
            </p>
          </div>
        </div>

        <details open class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <summary class="cursor-pointer text-lg font-semibold text-slate-900">Berechnung und Datenbasis anzeigen</summary>
          <div class="mt-4 space-y-5">
            <div class="rounded bg-slate-50 p-3 text-xs text-slate-700">
              <p class="font-semibold">Formel</p>
              <p>
                Gesamt = (Klima×{{ form.climate_weight }} + Luft×{{ form.air_weight }} + Sicherheit×{{ form.safety_weight
                }} + Demografie×{{ form.demographics_weight }} + Alltagsnähe×{{ form.amenities_weight }} + Flächennutzung×{{ form.landuse_weight }} + ÖPNV×{{
                  form.oepnv_weight
                }}) / {{ weightSum }}
              </p>
              <p v-if="form.preset === 'urban'" class="mt-2">
                Urban-Profilscore = gewichteter Score × 0,80 + Urbanitätsfaktor × 0,20.
              </p>
            </div>

            <h2 class="text-base font-semibold">Welche Werte dahinterstehen</h2>
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
        </details>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import FinderFilterPanel from '~/components/FinderFilterPanel.vue'
import PreferenceForm from '~/components/PreferenceForm.vue'
import { activeFilterTags, buildPreferenceQuery, parsePreferenceQuery, preferenceQueryEquals } from '~/composables/usePreferenceQuery'
import { getGermanStateName } from '~/composables/useGermanStates'
import { usePreferencesStore } from '~/stores/preferences'
import { finderPresetMap } from '~/utils/finderPresets'

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

const categoryWeightRows = computed(() => [
  { key: 'climate', label: 'Klima', weight: form.value.climate_weight, share: effectiveWeights.value.climate, barClass: 'bg-amber-500' },
  { key: 'air', label: 'Luftqualität', weight: form.value.air_weight, share: effectiveWeights.value.air, barClass: 'bg-sky-500' },
  { key: 'safety', label: 'Sicherheit', weight: form.value.safety_weight, share: effectiveWeights.value.safety, barClass: 'bg-rose-500' },
  { key: 'demographics', label: 'Demografie', weight: form.value.demographics_weight, share: effectiveWeights.value.demographics, barClass: 'bg-violet-500' },
  { key: 'amenities', label: 'Alltagsnähe', weight: form.value.amenities_weight, share: effectiveWeights.value.amenities, barClass: 'bg-emerald-500' },
  { key: 'landuse', label: 'Fläche', weight: form.value.landuse_weight, share: effectiveWeights.value.landuse, barClass: 'bg-orange-500' },
  { key: 'oepnv', label: 'ÖPNV', weight: form.value.oepnv_weight, share: effectiveWeights.value.oepnv, barClass: 'bg-indigo-500' }
])

const allWeightBars = computed(() => categoryWeightRows.value)

const topWeightedCategories = computed(() => {
  const weighted = categoryWeightRows.value
    .filter((entry) => entry.weight > 0)
    .sort((left, right) => {
      if (right.weight !== left.weight) {
        return right.weight - left.weight
      }
      return right.share - left.share
    })
    .slice(0, 3)

  return weighted.length ? weighted : categoryWeightRows.value.slice(0, 3)
})

const activePreset = computed(() => (form.value.preset ? finderPresetMap[form.value.preset] : null))
const activePresetTitle = computed(() => activePreset.value?.label || 'Individuelles Profil')
const activePresetDescription = computed(() => {
  if (activePreset.value) {
    return form.value.preset === 'urban'
      ? `${activePreset.value.description} Zusätzlich fließt ein begrenzter Urbanitätsfaktor aus der Einwohnerzahl ein.`
      : activePreset.value.description
  }

  return 'Du hast die Gewichte selbst angepasst. Das Ranking folgt genau dieser individuellen Mischung.'
})
const activePresetPanelClass = computed(() => activePreset.value ? activePreset.value.theme.cardClass : 'bg-slate-50')
const activePresetBadgeClass = computed(() => activePreset.value ? activePreset.value.theme.badgeClass : 'bg-slate-100 text-slate-700')

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

const currentFilterText = computed(() => {
  const tags = activeFilterTags(form.value, selectedStateText.value)
  return tags.length ? tags.join(' · ') : 'Keine Filter aktiv.'
})

const selectedStateText = computed(() => {
  if (!form.value.state_code) {
    return 'Deutschland'
  }
  return getGermanStateName(form.value.state_code)
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

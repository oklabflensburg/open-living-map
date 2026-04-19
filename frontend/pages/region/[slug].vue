<template>
  <section v-if="detail" class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold">{{ detail.region.name }}</h1>
      <p class="text-sm text-slate-500">
        AGS {{ detail.region.ars }} · {{ detail.region.state_name }}
        <template v-if="detail.region.district_name"> · {{ detail.region.district_name }}</template>
      </p>
      <div v-if="detail.region.wikipedia_url || detail.region.wikidata_url" class="mt-3 flex flex-wrap gap-3 text-sm">
        <a v-if="detail.region.wikipedia_url" :href="detail.region.wikipedia_url" target="_blank" rel="noreferrer"
          class="font-medium text-sky-700 underline decoration-sky-300 underline-offset-4">
          Wikipedia
        </a>
        <a v-if="detail.region.wikidata_url" :href="detail.region.wikidata_url" target="_blank" rel="noreferrer"
          class="font-medium text-sky-700 underline decoration-sky-300 underline-offset-4">
          Wikidata<span v-if="detail.region.wikidata_id"> ({{ detail.region.wikidata_id }})</span>
        </a>
      </div>
    </div>

    <div class="grid gap-3 md:grid-cols-2">
      <ScoreBar label="Gesamt" :value="detail.scores.total || 0" card-class="border-slate-300 bg-slate-100"
        badge-class="bg-slate-800 text-white" bar-class="bg-slate-800" />
      <ScoreBar label="Klima" :value="detail.scores.climate || 0" card-class="border-amber-200 bg-amber-50/70"
        badge-class="bg-amber-100 text-amber-800" bar-class="bg-amber-600" />
      <ScoreBar label="Luft" :value="detail.scores.air || 0" card-class="border-sky-200 bg-sky-50/70"
        badge-class="bg-sky-100 text-sky-800" bar-class="bg-sky-600" />
      <ScoreBar label="Verkehrssicherheit" :value="detail.scores.safety || 0" card-class="border-rose-200 bg-rose-50/70"
        badge-class="bg-rose-100 text-rose-800" bar-class="bg-rose-600" />
      <ScoreBar label="Demografie" :value="detail.scores.demographics || 0" card-class="border-violet-200 bg-violet-50/70"
        badge-class="bg-violet-100 text-violet-800" bar-class="bg-violet-600" />
      <ScoreBar label="Alltagsnähe" :value="detail.scores.amenities || 0" card-class="border-emerald-200 bg-emerald-50/70"
        badge-class="bg-emerald-100 text-emerald-800" bar-class="bg-emerald-600" />
      <ScoreBar label="Flächennutzung" :value="detail.scores.landuse || 0" card-class="border-orange-200 bg-orange-50/70"
        badge-class="bg-orange-100 text-orange-800" bar-class="bg-orange-600" />
      <ScoreBar label="ÖPNV" :value="detail.scores.oepnv || 0" card-class="border-indigo-200 bg-indigo-50/70"
        badge-class="bg-indigo-100 text-indigo-800" bar-class="bg-indigo-600" />
    </div>

    <div class="rounded-xl border border-violet-200 bg-violet-50/60 p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Demografie gesamt</h2>
          <p class="text-sm text-slate-500">Gemeindedatensatz und Regionalstatistik für {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="demographicStats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article v-for="item in demographicStats" :key="item.label"
          class="rounded-lg border border-violet-200 bg-white/80 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ item.value }}</p>
          <p v-if="item.note" class="mt-1 text-xs text-slate-500">{{ item.note }}</p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Für diese Gemeinde sind aktuell keine zusammengefassten Demografie-Daten verfügbar.
      </p>
    </div>

    <div class="rounded-xl border border-amber-200 bg-amber-50/60 p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Flächenstatistik</h2>
          <p class="text-sm text-slate-500">Flächenatlas {{ detail.land_use_stat?.year ?? 2019 }} für {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="landUseStats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="item in landUseStats"
          :key="item.label"
          class="rounded-lg border border-amber-200 bg-white/80 p-4"
        >
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ item.value }}</p>
          <p v-if="item.note" class="mt-1 text-xs text-slate-500">{{ item.note }}</p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Für diese Gemeinde sind aktuell keine Flächenatlas-Daten geladen.
      </p>
    </div>

    <div class="rounded-xl border border-sky-200 bg-sky-50/60 p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Luftdaten-Stationen</h2>
          <p class="text-sm text-slate-500">Nächstgelegene UBA-Messstation je Schadstoff für {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="detail.air_stations.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article
          v-for="station in detail.air_stations"
          :key="station.indicator_key"
          class="cursor-pointer rounded-lg border p-4 transition"
          :class="selectedAirStationKey === station.indicator_key
            ? 'border-sky-400 bg-sky-50'
            : 'border-slate-200 bg-slate-50 hover:border-sky-300 hover:bg-sky-50/50'"
          @click="toggleAirStation(station.indicator_key)"
        >
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ station.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">
            {{ station.raw_value !== null ? formatAirValue(station.raw_value) : 'keine Daten' }}
          </p>
          <p class="mt-1 text-xs text-slate-500">Proxy aus der nächstgelegenen Station</p>
          <a
            :href="station.station_page_url || station.measures_url"
            target="_blank"
            rel="noreferrer"
            class="mt-4 block font-medium text-sky-700 underline decoration-sky-300 underline-offset-4"
          >
            Nächstgelegene Station: {{ station.station_name }}
            <span v-if="station.station_code">({{ station.station_code }})</span>
          </a>
          <p v-if="station.latitude !== null && station.longitude !== null" class="mt-1 text-xs text-slate-500">
            Koordinaten {{ formatStationCoordinate(station.latitude) }}, {{ formatStationCoordinate(station.longitude) }}
          </p>
          <p class="mt-1 text-xs text-slate-500">Stations-ID {{ station.station_id }}</p>
          <p class="mt-3 text-xs font-medium text-sky-700">
            {{ selectedAirStationKey === station.indicator_key ? 'Marker auf Karte fokussiert' : 'Marker auf Karte anzeigen' }}
          </p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Für diese Gemeinde sind aktuell keine Informationen zur nächstgelegenen UBA-Messstation geladen.
      </p>
    </div>

    <div class="rounded-xl border border-emerald-200 bg-emerald-50/60 p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">OSM-Alltagsnähe</h2>
          <p class="text-sm text-slate-500">POI-Kategorien für {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="detail.amenity_stats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="item in detail.amenity_stats" :key="item.category"
          class="cursor-pointer rounded-lg border p-4 transition" :class="selectedAmenityCategory === item.category
            ? 'border-emerald-400 bg-emerald-100'
            : 'border-emerald-200 bg-white/80 hover:border-emerald-300 hover:bg-emerald-50/80'
            " @click="toggleAmenityPois(item.category)">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ formatCount(item.count_total) }}</p>
          <p class="mt-3 text-xs font-medium text-emerald-700">
            {{ selectedAmenityCategory === item.category ? 'POIs auf Karte ausblenden' : 'POIs auf Karte anzeigen' }}
          </p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Für diese Gemeinde sind aktuell keine OSM-Alltagsnähe-Daten nach Kategorien geladen.
      </p>
    </div>

    <div class="rounded-xl border border-rose-200 bg-rose-50/60 p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Verkehrsunfälle</h2>
          <p class="text-sm text-slate-500">Unfallatlas-Kategorien für {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="detail.accident_stats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="item in detail.accident_stats" :key="item.category"
          class="cursor-pointer rounded-lg border p-4 transition" :class="selectedAccidentCategory === item.category
            ? 'border-rose-400 bg-rose-100'
            : 'border-rose-200 bg-white/80 hover:border-rose-300 hover:bg-rose-50/80'
            " @click="toggleAccidentPois(item.category)">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ formatCount(item.count_total) }}</p>
          <p class="mt-1 text-xs text-slate-500">gesamt</p>
          <p class="mt-3 text-xs font-medium text-rose-700">
            {{ selectedAccidentCategory === item.category ? 'Unfallorte auf Karte ausblenden' : 'Unfallorte auf Karte anzeigen' }}
          </p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Für diese Gemeinde sind aktuell keine Unfallatlas-Daten nach Kategorien geladen.
      </p>
    </div>

    <div class="rounded-xl border border-sky-200 bg-white p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Gemeindegrenze</h2>
          <p class="text-sm text-slate-500">BKG VG250 Gemeindegeometrie für {{ detail.region.name }}</p>
        </div>
        <p v-if="!detail.geometry" class="text-sm text-amber-700">
          Keine Polygongeometrie geladen. Führe `python -m app.etl.import_bkg` erneut aus.
        </p>
      </div>
      <RegionBoundaryMap :geometry="detail.geometry" :name="detail.region.name"
        :centroid-lat="detail.region.centroid_lat" :centroid-lon="detail.region.centroid_lon"
        :overlay-pois="activeOverlayPois" :selected-overlay-label="activeOverlayLabel"
        :air-stations="detail.air_stations" :selected-air-station-id="selectedAirStationId" />
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Berechnung und Datenbasis</h2>
      <p class="mt-2 text-sm text-slate-600">
        Die Detailseite nutzt ein neutrales Basisprofil mit Gewicht 1 je Kategorie. Die Finder-Ergebnisse verwenden
        deine individuell gesetzten Gewichtungen.
      </p>
      <div v-if="missingDemographics"
        class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Für diese Gemeinde sind aktuell keine Demografie-Indikatoren aus der Regionalstatistik geladen.
        Der Demografie-Score bleibt deshalb vorübergehend bei 0, bis der Gemeinde-Import erfolgreich durchgelaufen ist.
      </div>

      <div class="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Score-Formel</p>
        <p class="mt-1">{{ detail.score_formula }}</p>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Warum kommt dieses Ergebnis heraus?</p>
        <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
          <li v-for="item in detail.calculation_details" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div class="mt-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Rohdaten und normierte Teil-Scores</p>
        <div class="mt-3 grid gap-3 md:grid-cols-2">
          <article v-for="indicator in detail.indicators" :key="indicator.key"
            class="rounded-lg border p-3 shadow-sm"
            :class="indicatorCategoryTheme(indicator.category).cardClass">
            <div class="flex items-start justify-between gap-3">
              <h3 class="font-medium text-slate-900">{{ indicator.name }}</h3>
              <span class="rounded-full px-2.5 py-1 text-xs font-semibold"
                :class="indicatorCategoryTheme(indicator.category).badgeClass">
                {{ categoryLabel(indicator.category) }}
              </span>
            </div>
            <p class="mt-1 text-sm text-slate-700">{{ indicator.text }}</p>
            <p v-if="indicator.quality_flag !== 'ok'" class="mt-1 text-xs text-amber-700">
              Datenqualität: {{ indicator.quality_flag }}
            </p>
          </article>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-2 text-lg font-semibold">Highlights</h2>
      <ul class="list-disc space-y-1 pl-5 text-sm text-slate-700">
        <li v-for="item in detail.highlights" :key="item">{{ item }}</li>
      </ul>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-2 text-lg font-semibold">Quellen</h2>
      <SourceList :sources="detail.source_links" />
    </div>
  </section>

  <div v-else-if="pending" class="text-slate-500">Lade Region...</div>
  <div v-else class="text-red-600">Region nicht gefunden.</div>
</template>

<script setup lang="ts">
import ScoreBar from '~/components/ScoreBar.vue'
import SourceList from '~/components/SourceList.vue'
import RegionBoundaryMap from '~/components/RegionBoundaryMap.vue'
import type { GeoJsonFeatureCollection, RecommendationIndicatorDetail, RegionDetailResponse } from '~/types/api'

const { siteName, absoluteUrl } = useSiteSeo()
const route = useRoute()
const { fetchRegion, fetchAmenityPois, fetchAccidentPois } = useRegions()

const pending = ref(true)
const detail = ref<RegionDetailResponse | null>(null)
const amenityPois = ref<GeoJsonFeatureCollection | null>(null)
const selectedAmenityCategory = ref<string | null>(null)
const accidentPois = ref<GeoJsonFeatureCollection | null>(null)
const selectedAccidentCategory = ref<string | null>(null)
const selectedAirStationKey = ref<string | null>(null)

useSeoMeta({
  title: () => (detail.value ? `${detail.value.region.name}` : 'Region'),
  description: () =>
    detail.value
      ? `${detail.value.region.name} in ${detail.value.region.state_name}: Scores zu Klima, Luftqualität, Verkehrssicherheit, Demografie, Alltagsnähe und ÖPNV.`
      : 'Region im Wohnort-Kompass',
  ogUrl: () => absoluteUrl(`/region/${String(route.params.slug)}`),
  ogTitle: () => (detail.value ? `${detail.value.region.name} | ${siteName}` : `Region | ${siteName}`),
  ogDescription: () =>
    detail.value
      ? `${detail.value.region.name} in ${detail.value.region.state_name}: Scores zu Klima, Luftqualität, Verkehrssicherheit, Demografie, Alltagsnähe und ÖPNV.`
      : 'Region im Wohnort-Kompass',
  ogType: 'article',
  twitterTitle: () => (detail.value ? `${detail.value.region.name} | ${siteName}` : `Region | ${siteName}`),
  twitterDescription: () =>
    detail.value
      ? `${detail.value.region.name} in ${detail.value.region.state_name}: Scores zu Klima, Luftqualität, Verkehrssicherheit, Demografie, Alltagsnähe und ÖPNV.`
      : 'Region im Wohnort-Kompass',
  twitterCard: 'summary'
})

useHead(() => {
  const canonicalPath = `/region/${String(route.params.slug)}`
  const region = detail.value?.region
  const description = region
    ? `${region.name} in ${region.state_name}: Scores zu Klima, Luftqualität, Verkehrssicherheit, Demografie, Alltagsnähe und ÖPNV.`
    : 'Region im Wohnort-Kompass'

  const graph: Record<string, unknown>[] = [
    {
      '@type': 'WebPage',
      name: region ? `${region.name} | ${siteName}` : `Region | ${siteName}`,
      url: absoluteUrl(canonicalPath),
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
            name: region ? region.name : 'Region',
            item: absoluteUrl(canonicalPath)
          }
        ]
      },
      isPartOf: {
        '@id': `${absoluteUrl('/')}#website`
      }
    }
  ]

  if (region) {
    graph.push({
      '@type': 'AdministrativeArea',
      '@id': `${absoluteUrl(canonicalPath)}#administrative-area`,
      name: region.name,
      identifier: region.ars,
      containedInPlace: region.state_name,
      geo:
        region.centroid_lat !== null && region.centroid_lon !== null
          ? {
              '@type': 'GeoCoordinates',
              latitude: region.centroid_lat,
              longitude: region.centroid_lon
            }
          : undefined,
      sameAs: [region.wikipedia_url, region.wikidata_url].filter(Boolean)
    })
  }

  return {
    link: [{ rel: 'canonical', href: absoluteUrl(canonicalPath) }],
    script: [
      {
        key: 'ld-region',
        type: 'application/ld+json',
        children: JSON.stringify(graph.length === 1 ? { '@context': 'https://schema.org', ...graph[0] } : { '@context': 'https://schema.org', '@graph': graph })
      }
    ]
  }
})

const categoryLabels: Record<string, string> = {
  climate: 'Klima',
  air: 'Luftqualität',
  safety: 'Verkehrssicherheit',
  demographics: 'Demografie/Familie',
  amenities: 'Alltagsnähe',
  landuse: 'Flächennutzung',
  oepnv: 'ÖPNV'
}

const categoryThemes: Record<string, { cardClass: string; badgeClass: string }> = {
  climate: {
    cardClass: 'border-amber-200 bg-amber-50/70',
    badgeClass: 'bg-amber-100 text-amber-800'
  },
  air: {
    cardClass: 'border-sky-200 bg-sky-50/70',
    badgeClass: 'bg-sky-100 text-sky-800'
  },
  safety: {
    cardClass: 'border-rose-200 bg-rose-50/70',
    badgeClass: 'bg-rose-100 text-rose-800'
  },
  demographics: {
    cardClass: 'border-violet-200 bg-violet-50/70',
    badgeClass: 'bg-violet-100 text-violet-800'
  },
  amenities: {
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    badgeClass: 'bg-emerald-100 text-emerald-800'
  },
  landuse: {
    cardClass: 'border-orange-200 bg-orange-50/70',
    badgeClass: 'bg-orange-100 text-orange-800'
  },
  oepnv: {
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    badgeClass: 'bg-indigo-100 text-indigo-800'
  }
}

function categoryLabel(category: string) {
  return categoryLabels[category] || category
}

function indicatorCategoryTheme(category: string) {
  return categoryThemes[category] || {
    cardClass: 'border-slate-200 bg-white',
    badgeClass: 'bg-slate-100 text-slate-700'
  }
}

function formatCount(value: number) {
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 0 }).format(value)
}

function formatPercent(value: number) {
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value) + ' %'
}

function formatPer10k(value: number) {
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
}

function formatSquareMetersPerCapita(value: number) {
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value) + ' m² je Einwohner'
}

function formatAirValue(value: number) {
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value) + ' µg/m³'
}

function formatStationCoordinate(value: number) {
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 5, maximumFractionDigits: 5 }).format(value)
}

function indicatorByKey(key: string): RecommendationIndicatorDetail | null {
  return detail.value?.indicators.find((indicator) => indicator.key === key) ?? null
}

const missingDemographics = computed(() => {
  if (!detail.value || detail.value.region.level !== 'gemeinde') {
    return false
  }

  return !detail.value.indicators.some((indicator) => indicator.category === 'demographics')
})

const demographicStats = computed(() => {
  if (!detail.value) {
    return []
  }

  const items: Array<{ label: string; value: string; note?: string }> = []
  const population = detail.value.region.population ?? indicatorByKey('population_total_destatis')?.raw_value ?? null
  const femaleShare = indicatorByKey('female_share_destatis')
  const youthShare = indicatorByKey('youth_share_destatis')
  const seniorShare = indicatorByKey('senior_share_destatis')

  if (population !== null) {
    items.push({
      label: 'Einwohner gesamt',
      value: formatCount(population),
      note: detail.value.region.population !== null ? 'laut Gemeindedatensatz' : 'laut Destatis-Indikator'
    })
  }
  if (femaleShare) {
    items.push({
      label: 'Frauenanteil',
      value: formatPercent(femaleShare.raw_value),
      note: 'laut Destatis-Indikator'
    })
  }
  if (youthShare) {
    items.push({
      label: 'Unter 18 Jahre',
      value: formatPercent(youthShare.raw_value),
      note: 'laut Destatis-Indikator'
    })
  }
  if (seniorShare) {
    items.push({
      label: 'Ab 65 Jahren',
      value: formatPercent(seniorShare.raw_value),
      note: 'laut Destatis-Indikator'
    })
  }

  return items
})

const landUseStats = computed(() => {
  if (!detail.value?.land_use_stat) {
    return []
  }

  const stat = detail.value.land_use_stat
  const items: Array<{ label: string; value: string; note?: string }> = []

  if (stat.forest_share_pct !== null) {
    items.push({
      label: 'Waldanteil',
      value: formatPercent(stat.forest_share_pct),
      note: `Anteil an der Gemeindefläche (${stat.year})`
    })
  }
  if (stat.settlement_transport_share_pct !== null) {
    items.push({
      label: 'Siedlung und Verkehr',
      value: formatPercent(stat.settlement_transport_share_pct),
      note: `Anteil an der Gemeindefläche (${stat.year})`
    })
  }
  if (stat.agriculture_share_pct !== null) {
    items.push({
      label: 'Landwirtschaft',
      value: formatPercent(stat.agriculture_share_pct),
      note: `Anteil an der Gemeindefläche (${stat.year})`
    })
  }
  if (stat.transport_share_pct !== null) {
    items.push({
      label: 'Verkehrsfläche',
      value: formatPercent(stat.transport_share_pct),
      note: `Anteil an der Gemeindefläche (${stat.year})`
    })
  }
  if (stat.settlement_transport_sqm_per_capita !== null) {
    items.push({
      label: 'Siedlung und Verkehr je Einwohner',
      value: formatSquareMetersPerCapita(stat.settlement_transport_sqm_per_capita),
      note: `Quadratmeter je Einwohner (${stat.year})`
    })
  }

  return items
})

const selectedAmenityLabel = computed(() => {
  if (!detail.value || !selectedAmenityCategory.value) {
    return null
  }
  return detail.value.amenity_stats.find((item) => item.category === selectedAmenityCategory.value)?.label ?? null
})

const selectedAirStationId = computed(() => {
  if (!detail.value || !selectedAirStationKey.value) {
    return null
  }
  return detail.value.air_stations.find((station) => station.indicator_key === selectedAirStationKey.value)?.station_id ?? null
})

const selectedAccidentLabel = computed(() => {
  if (!detail.value || !selectedAccidentCategory.value) {
    return null
  }
  return detail.value.accident_stats.find((item) => item.category === selectedAccidentCategory.value)?.label ?? null
})

const activeOverlayPois = computed(() => accidentPois.value ?? amenityPois.value)
const activeOverlayLabel = computed(() => selectedAccidentLabel.value ?? selectedAmenityLabel.value)

async function toggleAmenityPois(category: string) {
  if (!detail.value) {
    return
  }

  if (selectedAmenityCategory.value === category) {
    selectedAmenityCategory.value = null
    amenityPois.value = null
    return
  }

  selectedAccidentCategory.value = null
  accidentPois.value = null
  selectedAirStationKey.value = null
  selectedAmenityCategory.value = category
  amenityPois.value = await fetchAmenityPois(String(route.params.slug), category)
}

async function toggleAccidentPois(category: string) {
  if (!detail.value) {
    return
  }

  if (selectedAccidentCategory.value === category) {
    selectedAccidentCategory.value = null
    accidentPois.value = null
    return
  }

  selectedAmenityCategory.value = null
  amenityPois.value = null
  selectedAirStationKey.value = null
  selectedAccidentCategory.value = category
  accidentPois.value = await fetchAccidentPois(String(route.params.slug), category)
}

function toggleAirStation(indicatorKey: string) {
  selectedAmenityCategory.value = null
  amenityPois.value = null
  selectedAccidentCategory.value = null
  accidentPois.value = null
  selectedAirStationKey.value = selectedAirStationKey.value === indicatorKey ? null : indicatorKey
}

onMounted(async () => {
  try {
    detail.value = await fetchRegion(String(route.params.slug))
  } finally {
    pending.value = false
  }
})
</script>

<template>
  <section v-if="detail" class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold">{{ detail.region.name }}</h1>
      <p class="text-sm text-slate-500">AGS {{ detail.region.ars }} · {{ detail.region.state_name }}</p>
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

    <div class="grid gap-3 rounded-xl border border-slate-200 bg-white p-6 md:grid-cols-2">
      <ScoreBar label="Gesamt" :value="detail.scores.total || 0" />
      <ScoreBar label="Klima" :value="detail.scores.climate || 0" />
      <ScoreBar label="Luft" :value="detail.scores.air || 0" />
      <ScoreBar label="Sicherheit" :value="detail.scores.safety || 0" />
      <ScoreBar label="Demografie" :value="detail.scores.demographics || 0" />
      <ScoreBar label="Alltagsnaehe" :value="detail.scores.amenities || 0" />
      <ScoreBar label="OEPNV" :value="detail.scores.oepnv || 0" />
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Demografie gesamt</h2>
          <p class="text-sm text-slate-500">Gemeindedatensatz und Regionalstatistik fuer {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="demographicStats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article v-for="item in demographicStats" :key="item.label"
          class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ item.value }}</p>
          <p v-if="item.note" class="mt-1 text-xs text-slate-500">{{ item.note }}</p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Fuer diese Gemeinde sind aktuell keine zusammengefassten Demografie-Daten verfuegbar.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">OSM-Alltagsnaehe</h2>
          <p class="text-sm text-slate-500">POI-Kategorien fuer {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="detail.amenity_stats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="item in detail.amenity_stats" :key="item.category"
          class="cursor-pointer rounded-lg border p-4 transition" :class="selectedAmenityCategory === item.category
              ? 'border-amber-400 bg-amber-50'
              : 'border-slate-200 bg-slate-50 hover:border-amber-300 hover:bg-amber-50/50'
            " @click="toggleAmenityPois(item.category)">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-semibold text-slate-900">{{ formatCount(item.count_total) }}</p>
          <p class="mt-3 text-xs font-medium text-amber-700">
            {{ selectedAmenityCategory === item.category ? 'POIs auf Karte ausblenden' : 'POIs auf Karte anzeigen' }}
          </p>
        </article>
      </div>
      <p v-else class="text-sm text-amber-700">
        Fuer diese Gemeinde sind aktuell keine OSM-Alltagsnaehe-Daten nach Kategorien geladen.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Verkehrsunfaelle</h2>
          <p class="text-sm text-slate-500">Unfallatlas-Kategorien fuer {{ detail.region.name }}</p>
        </div>
      </div>

      <div v-if="detail.accident_stats.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="item in detail.accident_stats" :key="item.category"
          class="cursor-pointer rounded-lg border p-4 transition" :class="selectedAccidentCategory === item.category
              ? 'border-rose-400 bg-rose-50'
              : 'border-slate-200 bg-slate-50 hover:border-rose-300 hover:bg-rose-50/50'
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
        Fuer diese Gemeinde sind aktuell keine Unfallatlas-Daten nach Kategorien geladen.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-lg font-semibold">Gemeindegrenze</h2>
          <p class="text-sm text-slate-500">BKG VG250 Gemeindegeometrie für {{ detail.region.name }}</p>
        </div>
        <p v-if="!detail.geometry" class="text-sm text-amber-700">
          Keine Polygongeometrie geladen. Fuehre `python -m app.etl.import_bkg` erneut aus.
        </p>
      </div>
      <RegionBoundaryMap :geometry="detail.geometry" :name="detail.region.name"
        :centroid-lat="detail.region.centroid_lat" :centroid-lon="detail.region.centroid_lon"
        :overlay-pois="activeOverlayPois" :selected-overlay-label="activeOverlayLabel" />
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Berechnung und Datenbasis</h2>
      <p class="mt-2 text-sm text-slate-600">
        Die Detailseite nutzt ein neutrales Basisprofil mit Gewicht 1 je Kategorie. Die Finder-Ergebnisse verwenden
        deine individuell gesetzten Gewichtungen.
      </p>
      <div v-if="missingDemographics"
        class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Fuer diese Gemeinde sind aktuell keine Demografie-Indikatoren aus der Regionalstatistik geladen.
        Der Demografie-Score bleibt deshalb voruebergehend bei 0, bis der Gemeinde-Import erfolgreich durchgelaufen ist.
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
            class="rounded-lg border border-slate-200 bg-white p-3">
            <div class="flex items-start justify-between gap-3">
              <h3 class="font-medium">{{ indicator.name }}</h3>
              <span class="text-xs text-slate-500">{{ categoryLabel(indicator.category) }}</span>
            </div>
            <p class="mt-1 text-sm text-slate-600">{{ indicator.text }}</p>
            <p v-if="indicator.quality_flag !== 'ok'" class="mt-1 text-xs text-amber-700">
              Datenqualitaet: {{ indicator.quality_flag }}
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

const route = useRoute()
const { fetchRegion, fetchAmenityPois, fetchAccidentPois } = useRegions()

const pending = ref(true)
const detail = ref<RegionDetailResponse | null>(null)
const amenityPois = ref<GeoJsonFeatureCollection | null>(null)
const selectedAmenityCategory = ref<string | null>(null)
const accidentPois = ref<GeoJsonFeatureCollection | null>(null)
const selectedAccidentCategory = ref<string | null>(null)

const categoryLabels: Record<string, string> = {
  climate: 'Klima',
  air: 'Luft',
  safety: 'Sicherheit',
  demographics: 'Demografie',
  amenities: 'Alltagsnaehe',
  oepnv: 'OEPNV'
}

function categoryLabel(category: string) {
  return categoryLabels[category] || category
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

const selectedAmenityLabel = computed(() => {
  if (!detail.value || !selectedAmenityCategory.value) {
    return null
  }
  return detail.value.amenity_stats.find((item) => item.category === selectedAmenityCategory.value)?.label ?? null
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
  selectedAccidentCategory.value = category
  accidentPois.value = await fetchAccidentPois(String(route.params.slug), category)
}

onMounted(async () => {
  try {
    detail.value = await fetchRegion(String(route.params.slug))
  } finally {
    pending.value = false
  }
})
</script>

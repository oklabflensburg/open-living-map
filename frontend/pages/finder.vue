<template>
  <section class="mx-auto max-w-4xl space-y-6">
    <h1 class="mb-4 text-2xl font-bold">Gewichtungen festlegen</h1>

    <div class="grid gap-6 lg:grid-cols-2">
      <PreferenceForm v-model="form" @submit="submit" />

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
            }} + Demografie×{{ form.demographics_weight }} + Alltagsnähe×{{ form.amenities_weight }} + OEPNV×{{
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
          OEPNV {{ effectiveWeights.oepnv }}%
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 class="mb-4 text-lg font-semibold">Welche Werte dahinterstehen</h2>
      <div class="grid gap-4 md:grid-cols-2">
        <article v-for="item in categoryDetails" :key="item.key" class="rounded border border-slate-200 p-4">
          <h3 class="font-semibold">{{ item.title }}</h3>
          <p class="mt-1 text-sm text-slate-600">{{ item.description }}</p>
          <p class="mt-2 text-xs text-slate-500">Indikatoren: {{ item.indicators.join(', ') }}</p>
          <p class="mt-1 text-xs text-slate-500">Richtung: {{ item.direction }}</p>
        </article>
      </div>

      <p class="mt-4 text-xs text-slate-500">
        Hinweis: Alle Indikatoren werden auf 0..100 normiert. Danach wird pro Kategorie gemittelt und anschließend
        mit deinen Gewichten verrechnet.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import PreferenceForm from '~/components/PreferenceForm.vue'
import { usePreferencesStore } from '~/stores/preferences'

const store = usePreferencesStore()
const router = useRouter()
const form = ref({ ...store.$state })

const weightSum = computed(() => {
  const sum =
    form.value.climate_weight +
    form.value.air_weight +
    form.value.safety_weight +
    form.value.demographics_weight +
    form.value.amenities_weight +
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
    form.value.oepnv_weight
  if (sum === 0) {
    return { climate: 0, air: 0, safety: 0, demographics: 0, amenities: 0, oepnv: 0 }
  }
  return {
    climate: Math.round((form.value.climate_weight / sum) * 100),
    air: Math.round((form.value.air_weight / sum) * 100),
    safety: Math.round((form.value.safety_weight / sum) * 100),
    demographics: Math.round((form.value.demographics_weight / sum) * 100),
    amenities: Math.round((form.value.amenities_weight / sum) * 100),
    oepnv: Math.round((form.value.oepnv_weight / sum) * 100)
  }
})

const categoryDetails = [
  {
    key: 'climate',
    title: 'Klima',
    description: 'Klimatische Belastung und Niederschlag auf Kreisebene (DWD).',
    indicators: ['heat_days', 'summer_days', 'precipitation_proxy'],
    direction: 'Weniger Hitzetage besser, mehr Niederschlag/Sommertage je nach Indikator.'
  },
  {
    key: 'air',
    title: 'Luftqualität',
    description: 'Luftschadstoffe aus UBA-Stationen, auf Kreise aggregiert.',
    indicators: ['no2', 'pm10', 'pm25'],
    direction: 'Niedriger ist besser.'
  },
  {
    key: 'safety',
    title: 'Verkehrssicherheit',
    description: 'Unfallatlas-Unfallorte pro Kreis (Destatis).',
    indicators: ['road_accidents_total'],
    direction: 'Niedriger ist besser.'
  },
  {
    key: 'demographics',
    title: 'Demografie/Familie',
    description: 'Kreisindikatoren aus GENESIS (Bevölkerung, Altersstruktur, Geschlechteranteil).',
    indicators: ['population_total_destatis', 'female_share_destatis', 'youth_share_destatis', 'senior_share_destatis'],
    direction: 'Je nach Kennzahl höher oder niedriger besser.'
  },
  {
    key: 'amenities',
    title: 'Alltagsnähe',
    description: 'POI-Dichte aus OSM je Kreis.',
    indicators: ['amenities_density'],
    direction: 'Höher ist besser.'
  },
  {
    key: 'oepnv',
    title: 'OEPNV',
    description: 'ÖPNV-Haltestellen, Abfahrtsdichte und Regelmäßigkeit aus GTFS.',
    indicators: ['oepnv_stop_density', 'oepnv_departures_per_10k', 'oepnv_departure_regularity'],
    direction: 'Höher ist besser.'
  }
]

function submit() {
  store.setWeight('climate_weight', form.value.climate_weight)
  store.setWeight('air_weight', form.value.air_weight)
  store.setWeight('safety_weight', form.value.safety_weight)
  store.setWeight('demographics_weight', form.value.demographics_weight)
  store.setWeight('amenities_weight', form.value.amenities_weight)
  store.setWeight('oepnv_weight', form.value.oepnv_weight)
  store.setStateCode(form.value.state_code)
  router.push('/results')
}
</script>

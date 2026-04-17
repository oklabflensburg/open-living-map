<template>
  <section class="space-y-6">
    <h1 class="text-2xl font-bold">Methodik und Datenquellen</h1>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-2 text-lg font-semibold">Transparenz</h2>
      <p class="text-sm text-slate-700">
        Alle Indikatoren werden auf 0 bis 100 normiert. Je nach Indikator gilt `higher_is_better` oder
        `lower_is_better`. Kategorie-Scores sind Mittelwerte ihrer Indikatoren, der Gesamtscore ist ein gewichteter
        Mittelwert der 6 Kategorien.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-2 text-lg font-semibold">Datenquellen</h2>
      <SourceList :sources="sources" />
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-2 text-lg font-semibold">Lizenzhinweise</h2>
      <p class="text-sm text-slate-700">
        OSM-basierte Daten unterliegen der ODbL. Attribution siehe
        <a href="https://www.openstreetmap.org/copyright?locale=de" class="text-blue-700 underline" target="_blank">OSM Copyright</a>.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import SourceList from '~/components/SourceList.vue'

const sources = [
  'https://www.destatis.de/DE/Service/OpenData/karten-geodaten.html',
  'https://www-genesis.destatis.de/datenbank/online#modal=web-service-api',
  'https://opendata.dwd.de/',
  'https://luftdaten.umweltbundesamt.de/',
  'https://www.opendata-oepnv.de/ht/de/datensaetze',
  'https://download.geofabrik.de/europe/germany.html',
  'https://sgx.geodatenzentrum.de/wfs_vg250'
]
</script>

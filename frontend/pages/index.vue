<template>
  <section class="grid gap-8 md:grid-cols-2 md:items-center">
    <div>
      <p class="mb-2 inline-block rounded bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
        MVP Deutschland
      </p>
      <h1 class="text-4xl font-black tracking-tight text-slate-900">
        Finde passende Kreise und kreisfreie Staedte fuer deinen Alltag.
      </h1>
      <p class="mt-4 text-slate-600">
        Wohnort-Kompass kombiniert offene Daten aus Klima, Luft, Sicherheit, Demografie, Alltagsnaehe und OePNV.
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
        <li>Regionale Teil-Scores mit nachvollziehbarer Begruendung</li>
        <li>Vergleich von bis zu 3 Regionen</li>
      </ul>
    </div>
  </section>
</template>

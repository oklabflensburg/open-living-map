<template>
  <section class="space-y-6">
    <h1 class="text-2xl font-bold">Methodik und Datenquellen</h1>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">Worum es bei der Methodik geht</h2>
      <div class="space-y-3 text-sm text-slate-700">
        <p>
          Wohnort-Kompass vergleicht Regionen in Deutschland auf Basis offener Datenquellen. Das Ziel ist nicht,
          einen „objektiv besten“ Ort zu bestimmen, sondern eine nachvollziehbare, datenbasierte Vorauswahl zu
          ermöglichen.
        </p>
        <p>
          Dafür werden Rohdaten aus mehreren Quellen importiert, auf gemeinsame Regionen bezogen, in normierte
          Teil-Scores übersetzt und anschließend mit deinen Gewichten zu einem persönlichen Gesamtscore verrechnet.
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">Der Prozess in 5 Schritten</h2>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <article v-for="step in processSteps" :key="step.title"
          class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-sky-700">{{ step.kicker }}</p>
          <h3 class="mt-2 font-semibold text-slate-900">{{ step.title }}</h3>
          <p class="mt-2 text-sm text-slate-700">{{ step.text }}</p>
        </article>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">1. Regionen als gemeinsame Basis</h2>
      <div class="space-y-3 text-sm text-slate-700">
        <p>
          Damit Daten aus verschiedenen Quellen zusammenpassen, braucht das System zuerst einen stabilen räumlichen
          Schlüssel. Diese Grundlage bildet der amtliche Gemeindeschlüssel beziehungsweise Regionalschlüssel
          (`AGS`/`ARS`).
        </p>
        <p>
          Die Gemeindegrenzen und Stammdaten werden aus dem BKG-Datensatz übernommen. Dadurch hat jede Region im
          System eine eindeutige Kennung, einen Namen, eine Geometrie, einen Mittelpunkt und einen Bezug zu ihrem
          Bundesland.
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">2. Import der Rohdaten je Themenfeld</h2>
      <div class="grid gap-4 lg:grid-cols-2">
        <article v-for="section in sourceSections" :key="section.title" class="rounded-lg border border-slate-200 p-4">
          <h3 class="font-semibold text-slate-900">{{ section.title }}</h3>
          <p class="mt-2 text-sm text-slate-700">{{ section.text }}</p>
          <p class="mt-2 text-xs text-slate-500">Typische Indikatoren: {{ section.indicators.join(', ') }}</p>
        </article>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">3. Normierung der Indikatoren auf 0 bis 100</h2>
      <div class="space-y-3 text-sm text-slate-700">
        <p>
          Die Rohdaten haben sehr unterschiedliche Einheiten: Mikrogramm pro Kubikmeter, Prozentwerte, absolute
          Einwohnerzahlen oder Dichten je 10.000 Einwohner. Um sie vergleichbar zu machen, wird jeder Indikator
          separat auf eine gemeinsame Skala von 0 bis 100 transformiert.
        </p>
        <p>
          Technisch geschieht das als lineare Min-Max-Normierung über alle Regionen eines Zeitstands:
          Der kleinste beobachtete Wert wird zu 0, der größte zu 100. Liegen alle Werte identisch vor, wird
          standardmäßig 50 vergeben.
        </p>
        <div class="rounded-lg bg-slate-50 p-4 text-xs text-slate-700">
          <p class="font-semibold">Vereinfachte Formel</p>
          <p class="mt-1">Score = ((Wert − Minimum) / (Maximum − Minimum)) × 100</p>
          <p class="mt-2">
            Für Indikatoren mit `lower_is_better` wird das Ergebnis anschließend invertiert. Dann gilt also:
            wenig NO₂, wenig PM10, wenig Unfälle oder wenig Hitzetage ergeben einen höheren Score.
          </p>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">4. Bildung der Kategorie-Scores</h2>
      <div class="space-y-4 text-sm text-slate-700">
        <p>
          Jeder importierte Indikator gehört genau zu einer von sechs Kategorien:
          Klima, Luftqualität, Verkehrssicherheit, Demografie/Familie, Alltagsnähe und ÖPNV.
        </p>
        <p>
          Innerhalb einer Kategorie wird nicht noch einmal kompliziert gewichtet. Stattdessen bildet das System
          den einfachen Mittelwert der normierten Indikatoren, die in dieser Kategorie für die Region vorliegen.
          Fehlen für eine Kategorie alle Werte, erhält die Region dort aktuell 0 Punkte.
        </p>
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <article v-for="category in categories" :key="category.title"
            class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <h3 class="font-semibold text-slate-900">{{ category.title }}</h3>
            <p class="mt-2 text-sm text-slate-700">{{ category.text }}</p>
            <p class="mt-2 text-xs text-slate-500">Aktuelle Indikatoren: {{ category.indicators.join(', ') }}</p>
          </article>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">5. Persönlicher Gesamtscore im Finder</h2>
      <div class="space-y-3 text-sm text-slate-700">
        <p>
          Auf der Detailseite wird zunächst ein neutrales Basisprofil angezeigt. Dort zählt jede der sechs
          Kategorien gleich stark. Im Finder setzt du dann eigene Gewichte von 0 bis 5.
        </p>
        <p>
          Der persönliche Gesamtscore ist ein gewichteter Mittelwert der sechs Kategorie-Scores. Kategorien mit
          Gewicht 0 fließen nicht ein. Wenn alle Gewichte 0 sind, ergibt sich konsequent ein Gesamtscore von 0.
        </p>
        <div class="rounded-lg bg-slate-50 p-4 text-xs text-slate-700">
          <p class="font-semibold">Vereinfachte Finder-Formel</p>
          <p class="mt-1">
            Gesamtscore = (Klima × Gewicht + Luft × Gewicht + Sicherheit × Gewicht + Demografie × Gewicht +
            Alltagsnähe × Gewicht + ÖPNV × Gewicht) / Summe aller Gewichte
          </p>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">Wie die Detailseite ihre Erklärungen bildet</h2>
      <div class="space-y-3 text-sm text-slate-700">
        <p>
          Die Detailseite zeigt nicht nur den Score, sondern auch den Rechenweg. Dazu werden die gespeicherten
          Rohwerte und normierten Werte je Indikator geladen und in Textbausteine übersetzt.
        </p>
        <p>
          Zusätzlich werden in einzelnen Bereichen fachliche Zusatzinformationen ergänzt, zum Beispiel:
        </p>
        <ul class="list-disc space-y-1 pl-5">
          <li>Demografie-Werte aus Gemeindedatensatz oder Regionalstatistik</li>
          <li>OSM-Alltagsnähe nach Kategorien wie Apotheken, Kitas, Bahnhöfe oder Bibliotheken</li>
          <li>Unfallatlas-Kategorien nach Schwere</li>
          <li>nächstgelegene UBA-Messstationen für NO₂, PM10 und PM2.5</li>
        </ul>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">Wichtige Grenzen der Methodik</h2>
      <div class="grid gap-4 md:grid-cols-2">
        <article v-for="limit in limitations" :key="limit.title"
          class="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h3 class="font-semibold text-amber-950">{{ limit.title }}</h3>
          <p class="mt-2 text-sm text-amber-900">{{ limit.text }}</p>
        </article>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">Datenquellen</h2>
      <SourceList :sources="sources" />
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="mb-3 text-lg font-semibold">Lizenzhinweise</h2>
      <div class="space-y-3 text-sm text-slate-700">
        <p>
          OSM-basierte Daten unterliegen der ODbL. Attribution siehe
          <a href="https://www.openstreetmap.org/copyright?locale=de" class="text-blue-700 underline"
            target="_blank">OSM Copyright</a>.
        </p>
        <p>
          Weitere Hinweise zu Lizenzen und Attribution der genutzten Datenquellen stehen in der README des Projekts.
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import SourceList from '~/components/SourceList.vue'

const { siteName, absoluteUrl } = useSiteSeo()

const title = 'Methodik'
const description =
  'Dokumentation der Indikatoren, Datenquellen, Normierung und Lizenzhinweise von Wohnort-Kompass.'

useSeoMeta({
  title,
  description,
  ogUrl: absoluteUrl('/methodik'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'article',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl('/methodik') }],
  script: [
    {
      key: 'ld-methodik',
      type: 'application/ld+json',
      children: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'TechArticle',
        headline: `${title} | ${siteName}`,
        url: absoluteUrl('/methodik'),
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
              item: absoluteUrl('/methodik')
            }
          ]
        }
      })
    }
  ]
}))

const sources = [
  'https://sgx.geodatenzentrum.de/wfs_vg250-ew',
  'https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:ags',
  'https://www.regionalstatistik.de/genesis/online',
  'https://www.regionalstatistik.de/genesisws/rest/2020/data/table',
  'https://opendata.dwd.de/',
  'https://luftdaten.umweltbundesamt.de/api/air-data/v4/doc',
  'https://www.env-it.de/stationen/public/station.do',
  'https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/',
  'https://www.destatis.de/DE/Service/Statistik-Visualisiert/unfall-atlas.html',
  'https://download.geofabrik.de/europe/germany.html',
  'https://www.openstreetmap.org/copyright?locale=de',
  'https://www.opendata-oepnv.de/ht/de/datensaetze',
  'https://query.wikidata.org/sparql',
  'https://www.wikidata.org/wiki/Wikidata:Main_Page',
  'https://de.wikipedia.org/'
]

const processSteps = [
  {
    kicker: 'Schritt 1',
    title: 'Regionen aufbauen',
    text: 'Gemeinde- und Regionsgrenzen werden mit AGS/ARS als gemeinsamer Schlüssel importiert.'
  },
  {
    kicker: 'Schritt 2',
    title: 'Rohdaten laden',
    text: 'Fachliche Datensätze aus Klima, Luft, Demografie, OSM, Unfallatlas und ÖPNV werden regional zugeordnet.'
  },
  {
    kicker: 'Schritt 3',
    title: 'Werte normieren',
    text: 'Jeder Indikator wird auf eine Skala von 0 bis 100 transformiert, damit unterschiedliche Einheiten vergleichbar werden.'
  },
  {
    kicker: 'Schritt 4',
    title: 'Kategorie-Scores bilden',
    text: 'Die normierten Indikatoren werden je Kategorie gemittelt und als Snapshot gespeichert.'
  },
  {
    kicker: 'Schritt 5',
    title: 'Persönlich gewichten',
    text: 'Im Finder werden die Kategorie-Scores nach deinen Präferenzen gewichtet und zu einem Ranking sortiert.'
  }
]

const sourceSections = [
  {
    title: 'Klima und Wetter',
    text: 'DWD-Daten liefern klimatische Belastungsindikatoren wie Hitzetage, Sommertage und einen Niederschlags-Proxy. Diese Werte werden regional zusammengeführt und so aufbereitet, dass sie als Vergleichsindikatoren für alle Regionen nutzbar sind.',
    indicators: ['heat_days', 'summer_days', 'precipitation_proxy']
  },
  {
    title: 'Luftqualität',
    text: 'Die Luftdaten stammen aus dem Umweltbundesamt. Für jede Region werden Schadstoffwerte aus der nächstgelegenen UBA-Messstation zugeordnet. Zusätzlich wird die zugehörige Station mit Name und Koordinaten auf der Detailseite angezeigt.',
    indicators: ['no2', 'pm10', 'pm25']
  },
  {
    title: 'Verkehrssicherheit',
    text: 'Die Unfalldaten kommen aus dem Unfallatlas. Unfallorte werden regional aggregiert und nach Schwereklassen gespeichert. Im Score fließt aktuell die regionale Unfallbelastung ein, in der Detailansicht zusätzlich die kategorisierten Unfallorte.',
    indicators: ['road_accidents_total']
  },
  {
    title: 'Demografie und Bevölkerung',
    text: 'Demografie-Werte werden aus Destatis beziehungsweise der Regionalstatistik geladen. Je nach Datenverfügbarkeit können absolute Einwohnerwerte, Frauenanteil und Altersstruktur auf Gemeindeebene oder als Indikator-Fallback angezeigt werden.',
    indicators: ['population_total_destatis', 'female_share_destatis', 'youth_share_destatis', 'senior_share_destatis']
  },
  {
    title: 'Alltagsnähe aus OSM',
    text: 'OpenStreetMap wird genutzt, um alltagsrelevante Einrichtungen innerhalb einer Region zu zählen und auf die Einwohnerzahl zu beziehen. Dazu gehören unter anderem Apotheken, Schulen, Haltestellen, Bibliotheken, Parks oder Restaurants.',
    indicators: ['amenities_density']
  },
  {
    title: 'ÖPNV',
    text: 'GTFS-Daten aus OpenData-ÖPNV werden ausgewertet, um Haltestellendichte, Abfahrten je 10.000 Einwohner und Regelmäßigkeit des Angebots zu berechnen.',
    indicators: ['oepnv_stop_density', 'oepnv_departures_per_10k', 'oepnv_departure_regularity']
  }
]

const categories = [
  {
    title: 'Klima',
    text: 'Misst klimatische Belastung und Wettercharakteristik. Weniger Hitzetage sind tendenziell besser; die Richtung wird pro Indikator festgelegt.',
    indicators: ['heat_days', 'summer_days', 'precipitation_proxy']
  },
  {
    title: 'Luftqualität',
    text: 'Misst Schadstoffbelastung anhand der nächstgelegenen UBA-Station. Niedrigere Werte ergeben höhere Scores.',
    indicators: ['no2', 'pm10', 'pm25']
  },
  {
    title: 'Verkehrssicherheit',
    text: 'Verdichtet Unfallbelastung in einen Sicherheitsscore. Weniger Unfälle sind besser.',
    indicators: ['road_accidents_total']
  },
  {
    title: 'Demografie/Familie',
    text: 'Bündelt Bevölkerungsstruktur, Frauenanteil und Altersanteile. Diese Kategorie ist bewusst beschreibend und keine normative Bewertung einzelner Bevölkerungsgruppen.',
    indicators: ['population_total_destatis', 'female_share_destatis', 'youth_share_destatis', 'senior_share_destatis']
  },
  {
    title: 'Alltagsnähe',
    text: 'Misst die Dichte relevanter POIs und Einrichtungen in einer Region. Je mehr alltagsrelevante Infrastruktur vorhanden ist, desto höher der Score.',
    indicators: ['amenities_density']
  },
  {
    title: 'ÖPNV',
    text: 'Misst Erreichbarkeit und Angebotsqualität des öffentlichen Verkehrs anhand von Haltestellen und GTFS-Abfahrtsdaten.',
    indicators: ['oepnv_stop_density', 'oepnv_departures_per_10k', 'oepnv_departure_regularity']
  }
]

const limitations = [
  {
    title: 'Ein hoher Score ist keine Lebensqualitäts-Garantie',
    text: 'Das Modell bildet ausgewählte messbare Faktoren ab. Es ersetzt keine Ortsbesichtigung und berücksichtigt nicht alles, was für eine Wohnentscheidung wichtig ist, etwa Mieten, soziale Bindungen oder subjektive Atmosphäre.'
  },
  {
    title: 'Normierung ist immer relativ',
    text: 'Ein Score von 80 bedeutet nicht „absolut gut“, sondern vor allem: im Vergleich zu den anderen aktuell im Datensatz enthaltenen Regionen relativ stark.'
  },
  {
    title: 'Datenstände unterscheiden sich',
    text: 'Die Quellen stammen aus unterschiedlichen Veröffentlichungszyklen. Klima, Luft, OSM, Regionalstatistik und GTFS können zeitlich auseinanderliegen.'
  },
  {
    title: 'Fehlende Daten drücken einzelne Kategorien',
    text: 'Wenn für eine Region in einer Kategorie aktuell keine verwertbaren Werte vorliegen, fällt der Kategorie-Score derzeit auf 0. Das ist transparent, aber fachlich nicht dasselbe wie „schlecht“.'
  },
  {
    title: 'Regionale Nähe ist teilweise proxy-basiert',
    text: 'Bei UBA-Luftdaten oder manchen OSM-Aggregationen arbeitet das System mit der nächstgelegenen Station oder mit regionalen Dichten. Das ist sinnvoll für Vergleichszwecke, aber nicht identisch mit einer Messung an jeder Adresse.'
  },
  {
    title: 'Die Gewichtung verschiebt das Ergebnis bewusst',
    text: 'Das Ranking im Finder ist kein neutrales amtliches Gesamtergebnis, sondern eine personalisierte Sicht. Wer Klima hoch gewichtet, bekommt bewusst ein anderes Ranking als jemand mit Fokus auf ÖPNV oder Alltagsnähe.'
  }
]
</script>

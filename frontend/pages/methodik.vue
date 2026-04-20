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
        <article
          v-for="section in sourceSections"
          :key="section.title"
          class="rounded-lg border p-4"
          :class="section.cardClass"
        >
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
          Technisch geschieht das als logarithmische Min-Max-Normierung über alle Regionen eines Zeitstands:
          Zuerst werden die Rohwerte logarithmisch gestaucht, damit extreme Ausreißer die Skala nicht dominieren.
          Anschließend wird der kleinste beobachtete Wert zu 0 und der größte zu 100. Liegen alle Werte identisch
          vor, wird standardmäßig 50 vergeben.
        </p>
        <div class="rounded-lg bg-slate-50 p-4 text-xs text-slate-700">
          <p class="font-semibold">Vereinfachte Formel</p>
          <p class="mt-1">Score = ((log(1 + Wert) − Minimum) / (Maximum − Minimum)) × 100</p>
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
          Jeder importierte Indikator gehört genau zu einer von sieben Kategorien:
          Klima, Luftqualität, Verkehrssicherheit, Demografie/Familie, Alltagsnähe, Flächennutzung und ÖPNV.
        </p>
        <p>
          Innerhalb einer Kategorie werden die normierten Indikatoren in der Regel als Mittelwert zusammengeführt.
          Für einzelne Kategorien mit stark unterschiedlichen Kennzahlen nutzt das System jedoch eine fachlich
          begründete interne Gewichtung. Das betrifft aktuell insbesondere den ÖPNV, damit Dichte, absolute
          Angebotsmasse und Regelmäßigkeit gemeinsam abgebildet werden. Fehlen für eine Kategorie alle Werte,
          erhält die Region dort aktuell 0 Punkte.
        </p>
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <article
            v-for="category in categories"
            :key="category.title"
            class="rounded-lg border p-4"
            :class="category.cardClass"
          >
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
          Auf der Detailseite wird zunächst ein neutrales Basisprofil angezeigt. Dort zählt jede der sieben
          Kategorien gleich stark. Im Finder setzt du dann eigene Gewichte von 0 bis 5.
        </p>
        <p>
          Der persönliche Gesamtscore ist ein gewichteter Mittelwert der sieben Kategorie-Scores. Kategorien mit
          Gewicht 0 fließen nicht ein. Wenn alle Gewichte 0 sind, ergibt sich konsequent ein Gesamtscore von 0.
        </p>
        <div class="rounded-lg bg-slate-50 p-4 text-xs text-slate-700">
          <p class="font-semibold">Vereinfachte Finder-Formel</p>
          <p class="mt-1">
            Gesamtscore = (Klima × Gewicht + Luft × Gewicht + Verkehrssicherheit × Gewicht +
            Demografie/Familie × Gewicht + Alltagsnähe × Gewicht + Flächennutzung × Gewicht +
            ÖPNV × Gewicht) / Summe aller Gewichte
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
      <h2 class="mb-3 text-lg font-semibold">Datenquellen und Lizenzen</h2>
      <div class="grid gap-4 lg:grid-cols-2">
        <article
          v-for="source in licensedSources"
          :key="source.title"
          class="rounded-lg border border-slate-200 bg-slate-50 p-4"
        >
          <h3 class="font-semibold text-slate-900">{{ source.title }}</h3>
          <p class="mt-2 text-sm text-slate-700">{{ source.projectUse }}</p>
          <p class="mt-3 text-xs font-medium text-slate-500">Lizenz</p>
          <p class="mt-1 text-sm text-slate-700">{{ source.license }}</p>
          <p v-if="source.attribution" class="mt-3 text-xs font-medium text-slate-500">Empfohlene Quellenangabe</p>
          <p v-if="source.attribution" class="mt-1 text-sm text-slate-700">{{ source.attribution }}</p>
          <p v-if="source.note" class="mt-3 text-xs text-slate-600">{{ source.note }}</p>
          <div class="mt-3 flex flex-wrap gap-2 text-xs">
            <a
              v-for="link in source.links"
              :key="link"
              :href="link"
              target="_blank"
              rel="noreferrer"
              class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-slate-400"
            >{{ link }}</a>
          </div>
        </article>
      </div>
      <p class="mt-4 text-xs text-slate-500">
        Die Übersicht folgt inhaltlich der README des Projekts. Wo ein Dienst keine eigenständige Lizenz auf der
        Datensatzseite ausweist, ist das hier als Einordnung oder Ableitung aus der offiziellen Anbieter-Dokumentation
        gekennzeichnet.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
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

const licensedSources = [
  {
    title: 'OpenStreetMap und Geofabrik',
    projectUse: 'OpenStreetMap liefert die POI-Daten für Alltagsnähe und die Kartenbasis in Leaflet. Geofabrik wird für den Deutschland-Extrakt im OSM-Import genutzt.',
    license: 'Open Data Commons Open Database License (ODbL) 1.0',
    attribution: '© OpenStreetMap-Mitwirkende, ODbL 1.0',
    links: [
      'https://www.openstreetmap.org/copyright?locale=de',
      'https://download.geofabrik.de/europe/germany.html',
      'https://download.geofabrik.de/europe/germany-latest.osm.pbf'
    ]
  },
  {
    title: 'BKG VG25',
    projectUse: 'Das BKG liefert Gemeinde- und Bundeslandgeometrien als räumliche Grundlage des gesamten Projekts.',
    license: 'CC BY 4.0',
    attribution: '© BKG (Jahr des letzten Datenbezugs) CC BY 4.0',
    note: 'Bei veränderten Daten ist laut BKG zusätzlich ein Veränderungshinweis anzubringen.',
    links: [
      'https://sgx.geodatenzentrum.de/wfs_vg250-ew',
      'https://gdz.bkg.bund.de/index.php/default/digitale-geodaten/verwaltungsgebiete/verwaltungsgebiete-1-25-000-stand-31-12-vg25.html',
      'https://www.bkg.bund.de'
    ]
  },
  {
    title: 'Destatis, Regionalstatistik und XRepository',
    projectUse: 'Destatis und die Regionalstatistik liefern Demografie- und Referenzdaten. XRepository wird im ETL für AGS- und Kreis-Schlüsselräume genutzt.',
    license: 'Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)',
    attribution: 'Datenquelle: Statistisches Bundesamt (Destatis), Genesis-Online bzw. Destatis-Referenzdaten, <Abrufdatum>; Datenlizenz by-2-0',
    note: 'Für XRepository-Codelisten ist auf den Detailseiten keine eigenständige Lizenz ausgewiesen. Im Projekt werden sie daher als Destatis-Referenzdaten im Open-Data-Kontext von Destatis behandelt. Das ist eine Einordnung aus den offiziellen Destatis-Open-Data-Hinweisen.',
    links: [
      'https://www.regionalstatistik.de/genesis/online',
      'https://www.regionalstatistik.de/genesisws/rest/2020/data/table',
      'https://www.destatis.de/DE/Service/OpenData/_inhalt.html',
      'https://www.destatis.de/DE/Service/Impressum/copyright-genesis-online.html',
      'https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:ags',
      'https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:kreis',
      'https://www.xrepository.de/api/xrepository/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:kreis_2025-03-31/download/Kreis_2025-03-31.json'
    ]
  },
  {
    title: 'DWD',
    projectUse: 'Der Deutsche Wetterdienst liefert die Klimaindikatoren wie Hitzetage, Sommertage und Niederschlag.',
    license: 'CC BY 4.0',
    attribution: 'Quelle: Deutscher Wetterdienst (DWD)',
    note: 'Die konkrete Produktdokumentation des jeweils verwendeten Open-Data-Produkts ist zusätzlich zu beachten.',
    links: [
      'https://opendata.dwd.de/',
      'https://opendata.dwd.de/climate_environment/REA/Nutzungsbedingungen_German.pdf',
      'https://www.dwd.de/EN/ourservices/cdc/cdc.html'
    ]
  },
  {
    title: 'Umweltbundesamt Luftdaten',
    projectUse: 'Die Luftdaten-API des Umweltbundesamts liefert Messwerte für NO₂, PM10 und PM2.5 sowie Stationsmetadaten.',
    license: 'Für bereitgestellte Daten und Metadaten ist die Nutzung nach den Bedingungen des UBA-Dienstes zulässig; im Quellenvermerk muss das Umweltbundesamt genannt werden.',
    attribution: 'Quelle: Umweltbundesamt mit Daten der Messnetze der Länder und des Bundes',
    note: 'Die Website-Inhalte selbst stehen, soweit nicht anders gekennzeichnet, unter CC BY-NC-ND 4.0. Diese Website-Lizenz wird im Projekt nicht pauschal auf die Fachdaten übertragen.',
    links: [
      'https://luftdaten.umweltbundesamt.de/api/air-data/v4/doc',
      'https://luftdaten.umweltbundesamt.de/datenschutz-haftung-und-urheberrecht',
      'https://www.env-it.de/stationen/public/station.do'
    ]
  },
  {
    title: 'Unfallatlas',
    projectUse: 'Die Unfallatlas-Daten liefern Unfallorte und regionale Unfallbelastung für die Kategorie Verkehrssicherheit.',
    license: 'Datenlizenz Deutschland 2.0 für statistische Daten; für kartografische Anwendungen können zusätzliche Hinweise des Atlas gelten.',
    attribution: 'Quelle: Statistische Ämter des Bundes und der Länder / Unfallatlas',
    note: 'Die Zuordnung zu dl-de/by-2-0 folgt den allgemeinen Open-Data-Hinweisen des Statistikportals für statistische Daten.',
    links: [
      'https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/',
      'https://www.destatis.de/DE/Service/Statistik-Visualisiert/unfall-atlas.html',
      'https://www.statistikportal.de/de/open-data'
    ]
  },
  {
    title: 'Flächenatlas',
    projectUse: 'Der Flächenatlas liefert amtliche Kennzahlen zur Flächennutzung auf Gemeindeebene und bildet im Projekt die eigene Kategorie Flächennutzung.',
    license: 'Datenlizenz Deutschland 2.0 für die statistischen Daten; bei kartografischen Anwendungen gelten zusätzlich die Lizenzhinweise des jeweiligen Atlas.',
    attribution: 'Datenquelle: Statistisches Bundesamt (Destatis), Flächenatlas / Flächenerhebung, <Abrufdatum>; Datenlizenz by-2-0',
    note: 'Die Einordnung folgt den allgemeinen Destatis-Open-Data-Hinweisen für statistische Daten. Für den hier genutzten XLSX-Datensatz ist auf der Download-URL selbst keine separate Lizenzseite ausgewiesen.',
    links: [
      'https://service.destatis.de/DE/karten/flaechenatlas2019daten.xlsx',
      'https://www.destatis.de/DE/Service/Statistik-Visualisiert/flaechenatlas.html',
      'https://www.destatis.de/DE/Service/OpenData/_inhalt.html'
    ]
  },
  {
    title: 'OpenData ÖPNV und DELFI GTFS',
    projectUse: 'OpenData ÖPNV und DELFI liefern die GTFS-Fahrplandaten für Haltestellendichte, Abfahrten und Regelmäßigkeit.',
    license: 'Für DELFI laut OpenData-ÖPNV-Archiv: CC-BY in aktueller Fassung',
    attribution: 'Quelle: DELFI / OpenData ÖPNV gemäß Datensatzlizenz',
    note: 'Das Portal selbst hat keine einheitliche Lizenz für alle Datensätze. Maßgeblich bleibt immer die Lizenz des konkret verwendeten Anbieters oder Datensatzes.',
    links: [
      'https://www.opendata-oepnv.de/ht/de/datensaetze',
      'https://www.opendata-oepnv.de/fileadmin/datasets/delfi/20260413_fahrplaene_gesamtdeutschland_gtfs.zip',
      'https://archiv.opendata-oepnv.de/_Lizenz%20und%20Impressum.txt'
    ]
  },
  {
    title: 'Wikidata und Wikipedia',
    projectUse: 'Wikidata wird für die Anreicherung von Regionsmetadaten genutzt. Wikipedia wird im Projekt vor allem als ausgehender Link zur Region angezeigt.',
    license: 'Wikidata-Structured-Data: CC0. Wikipedia-Texte: CC BY-SA, soweit Inhalte direkt übernommen werden.',
    attribution: 'Bei direkter Textübernahme aus Wikipedia ist eine CC-BY-SA-konforme Attribution erforderlich. Für reine Verlinkung ist das nicht einschlägig.',
    note: 'Im Projekt werden aus Wikipedia selbst keine Fließtexte importiert, sondern nur Ziel-URLs erzeugt. Die eigentliche strukturierte Anreicherung erfolgt über Wikidata.',
    links: [
      'https://query.wikidata.org/sparql',
      'https://www.wikidata.org/wiki/Wikidata:Licensing',
      'https://de.wikipedia.org/',
      'https://wikimediafoundation.org/our-work/wikimedia-projects/wikipedia/'
    ]
  }
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
    text: 'Fachliche Datensätze aus Klima, Luft, Demografie, OSM, Unfallatlas, Flächenatlas und ÖPNV werden regional zugeordnet.'
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
    cardClass: 'border-amber-200 bg-amber-50/70',
    text: 'DWD-Daten liefern klimatische Belastungsindikatoren wie Hitzetage, Sommertage und einen Niederschlags-Proxy. Diese Werte werden regional zusammengeführt und so aufbereitet, dass sie als Vergleichsindikatoren für alle Regionen nutzbar sind.',
    indicators: ['Hitzetage', 'Sommertage', 'Niederschlag']
  },
  {
    title: 'Luftqualität',
    cardClass: 'border-sky-200 bg-sky-50/70',
    text: 'Die Luftdaten stammen aus dem Umweltbundesamt. Für jede Region werden Schadstoffwerte aus der nächstgelegenen UBA-Messstation zugeordnet. Zusätzlich wird die zugehörige Station mit Name und Koordinaten auf der Detailseite angezeigt.',
    indicators: ['NO₂', 'PM10', 'PM2.5']
  },
  {
    title: 'Verkehrssicherheit',
    cardClass: 'border-rose-200 bg-rose-50/70',
    text: 'Die Unfalldaten kommen aus dem Unfallatlas. Unfallorte werden regional aggregiert und nach Schwereklassen gespeichert. Im Score fließt aktuell die regionale Unfallbelastung ein, in der Detailansicht zusätzlich die kategorisierten Unfallorte.',
    indicators: ['Verkehrsunfälle gesamt']
  },
  {
    title: 'Demografie und Bevölkerung',
    cardClass: 'border-violet-200 bg-violet-50/70',
    text: 'Demografie-Werte werden aus Destatis beziehungsweise der Regionalstatistik geladen. Je nach Datenverfügbarkeit können absolute Einwohnerwerte, Frauenanteil und Altersstruktur auf Gemeindeebene oder als Indikator-Fallback angezeigt werden.',
    indicators: ['Einwohner gesamt', 'Frauenanteil', 'Anteil unter 18 Jahren', 'Anteil ab 65 Jahren']
  },
  {
    title: 'Alltagsnähe aus OSM',
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    text: 'OpenStreetMap wird genutzt, um alltagsrelevante Einrichtungen innerhalb einer Region zu zählen und auf die Einwohnerzahl zu beziehen. Dazu gehören unter anderem Apotheken, Schulen, Haltestellen, Bibliotheken, Parks oder Restaurants.',
    indicators: ['Alltagsnähe aus OSM-POIs']
  },
  {
    title: 'Flächennutzung',
    cardClass: 'border-orange-200 bg-orange-50/70',
    text: 'Der Flächenatlas liefert amtliche Kennzahlen zur Bodennutzung auf Gemeindeebene. Dazu gehören unter anderem Waldanteil, Landwirtschaftsanteil sowie Siedlungs- und Verkehrsflächenanteile. Diese Werte werden je Gemeinde übernommen, normiert und als eigene Kategorie bewertet.',
    indicators: [
      'Waldanteil',
      'Landwirtschaftsanteil',
      'Siedlungs- und Verkehrsflächenanteil',
      'Verkehrsflächenanteil',
      'Siedlungs- und Verkehrsfläche je Einwohner'
    ]
  },
  {
    title: 'ÖPNV',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    text: 'GTFS-Daten aus OpenData-ÖPNV werden ausgewertet, um Haltestellendichte, Abfahrten je 10.000 Einwohner, absolute Angebotsmasse und Regelmäßigkeit des Angebots zu berechnen. Dichte- und Angebotsmetriken werden logarithmisch normiert, damit kleine und große Netze fairer vergleichbar bleiben.',
    indicators: ['Haltestellendichte', 'Abfahrten je 10.000 Einwohner', 'Angebotsmasse', 'Abfahrtsregelmäßigkeit']
  }
]

const categories = [
  {
    title: 'Klima',
    cardClass: 'border-amber-200 bg-amber-50/70',
    text: 'Misst klimatische Belastung und Wettercharakteristik. Weniger Hitzetage sind tendenziell besser; die Richtung wird pro Indikator festgelegt.',
    indicators: ['Hitzetage', 'Sommertage', 'Niederschlag']
  },
  {
    title: 'Luftqualität',
    cardClass: 'border-sky-200 bg-sky-50/70',
    text: 'Misst Schadstoffbelastung anhand der nächstgelegenen UBA-Station. Niedrigere Werte ergeben höhere Scores.',
    indicators: ['NO₂', 'PM10', 'PM2.5']
  },
  {
    title: 'Verkehrssicherheit',
    cardClass: 'border-rose-200 bg-rose-50/70',
    text: 'Verdichtet Unfallbelastung in einen Sicherheitsscore. Weniger Unfälle sind besser.',
    indicators: ['Verkehrsunfälle gesamt']
  },
  {
    title: 'Demografie/Familie',
    cardClass: 'border-violet-200 bg-violet-50/70',
    text: 'Bündelt Bevölkerungsstruktur, Frauenanteil und Altersanteile. Diese Kategorie ist bewusst beschreibend und keine normative Bewertung einzelner Bevölkerungsgruppen.',
    indicators: ['Einwohner gesamt', 'Frauenanteil', 'Anteil unter 18 Jahren', 'Anteil ab 65 Jahren']
  },
  {
    title: 'Alltagsnähe',
    cardClass: 'border-emerald-200 bg-emerald-50/70',
    text: 'Misst die Dichte relevanter POIs und Einrichtungen in einer Region. Je mehr alltagsrelevante Infrastruktur vorhanden ist, desto höher der Score.',
    indicators: ['Alltagsnähe aus OSM-POIs']
  },
  {
    title: 'Flächennutzung',
    cardClass: 'border-orange-200 bg-orange-50/70',
    text: 'Misst Flächenstruktur und Flächeninanspruchnahme auf Gemeindeebene. Mehr Wald- und Landwirtschaftsfläche wirkt positiv, hohe Siedlungs-, Verkehrs- und Flächenverbräuche je Einwohner negativ.',
    indicators: [
      'Waldanteil',
      'Landwirtschaftsanteil',
      'Siedlungs- und Verkehrsflächenanteil',
      'Verkehrsflächenanteil',
      'Siedlungs- und Verkehrsfläche je Einwohner'
    ]
  },
  {
    title: 'ÖPNV',
    cardClass: 'border-indigo-200 bg-indigo-50/70',
    text: 'Misst Erreichbarkeit und Angebotsqualität des öffentlichen Verkehrs anhand von Haltestellendichte, Abfahrtsdichte, absoluter Angebotsmasse und Regelmäßigkeit. Die Kategorie nutzt bewusst eine interne Gewichtung, damit Metropolen und kleinere Städte nicht nur über reine Pro-Kopf-Dichte verglichen werden.',
    indicators: ['Haltestellendichte', 'Abfahrten je 10.000 Einwohner', 'Angebotsmasse', 'Abfahrtsregelmäßigkeit']
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

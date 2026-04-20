<template>
  <section class="mx-auto max-w-4xl space-y-6">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h1 class="text-2xl font-bold">Datenschutz</h1>
      <p class="mt-3 text-sm text-slate-700">
        Diese Seite beschreibt in komprimierter Form die Verarbeitung personenbezogener Daten innerhalb der
        öffentlich erreichbaren Webanwendung. Die Verantwortlichen- und Kontaktangaben kommen aus der
        Frontend-Konfiguration.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Verantwortliche Stelle</h2>
      <div class="mt-4 space-y-1 text-sm text-slate-700">
        <p class="font-medium text-slate-900">{{ legal.privacyController || legal.name || 'Bitte Privacy-Controller in .env setzen' }}</p>
        <p v-if="legal.street">{{ legal.street }}</p>
        <p v-if="postalLine">{{ postalLine }}</p>
        <p v-if="legal.country">{{ legal.country }}</p>
        <p v-if="legal.email">
          E-Mail:
          <a :href="`mailto:${legal.email}`" class="text-sky-700 underline">{{ legal.email }}</a>
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Zugriff auf die Website</h2>
      <div class="mt-4 space-y-3 text-sm text-slate-700">
        <p>
          Beim Aufruf der Website werden technisch notwendige Informationen verarbeitet, damit die Seite ausgeliefert
          werden kann. Dazu können insbesondere IP-Adresse, Zeitpunkt des Zugriffs, angefragte URL, Browserdaten und
          Server-Logs gehören.
        </p>
        <p v-if="legal.hostingProvider">
          Hosting-Provider: {{ legal.hostingProvider }}
          <span v-if="legal.hostingLocation">({{ legal.hostingLocation }})</span>
        </p>
        <p v-if="legal.hostingPolicyUrl">
          Weitere Informationen:
          <a :href="legal.hostingPolicyUrl" target="_blank" rel="noreferrer" class="text-sky-700 underline">
            Datenschutzhinweise des Hosting-Providers
          </a>
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Anfragen an die API</h2>
      <div class="mt-4 space-y-3 text-sm text-slate-700">
        <p>
          Die Anwendung verarbeitet Eingaben wie Gewichtungen im Finder, Regionsaufrufe oder Vergleichsanfragen, um
          daraus Antworten der API zu erzeugen. Diese Eingaben dienen ausschließlich der Berechnung und Darstellung der
          Ergebnisse.
        </p>
        <p>
          Soweit Server-Logs oder technische Diagnosedaten anfallen, geschieht dies zur Sicherstellung des Betriebs,
          zur Fehleranalyse und zur Absicherung des Angebots.
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Externe Inhalte und Datenquellen</h2>
      <div class="mt-4 space-y-3 text-sm text-slate-700">
        <p>
          Die Anwendung verlinkt auf externe Websites, etwa zu UBA-Messstationen, Wikipedia, Wikidata oder
          Open-Data-Portalen. Beim Anklicken solcher Links gelten die Datenschutzinformationen der jeweiligen
          Anbieter.
        </p>
        <p>
          Kartenkacheln werden über OpenStreetMap bezogen. Dabei kann deine IP-Adresse an die Tile-Server
          übermittelt werden, weil die Karte sonst nicht dargestellt werden kann.
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h2 class="text-lg font-semibold">Deine Rechte</h2>
      <div class="mt-4 space-y-3 text-sm text-slate-700">
        <p>
          Dir stehen nach Maßgabe der gesetzlichen Voraussetzungen insbesondere Rechte auf Auskunft, Berichtigung,
          Löschung, Einschränkung der Verarbeitung sowie Widerspruch zu.
        </p>
        <p v-if="legal.email">
          Für Datenschutzanfragen kannst du dich an
          <a :href="`mailto:${legal.email}`" class="text-sky-700 underline">{{ legal.email }}</a>
          wenden.
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const { siteName, absoluteUrl } = useSiteSeo()
const { legal, postalLine } = useLegalConfig()

const title = 'Datenschutz'
const description = 'Datenschutzhinweise für die Nutzung von Wohnort-Kompass.'

useSeoMeta({
  title,
  description,
  ogUrl: absoluteUrl('/datenschutz'),
  ogTitle: `${title} | ${siteName}`,
  ogDescription: description,
  ogType: 'article',
  twitterTitle: `${title} | ${siteName}`,
  twitterDescription: description,
  twitterCard: 'summary'
})

useHead(() => ({
  link: [{ rel: 'canonical', href: absoluteUrl('/datenschutz') }],
  script: [
    {
      key: 'ld-datenschutz',
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        name: `${title} | ${siteName}`,
        url: absoluteUrl('/datenschutz'),
        description
      })
    }
  ]
}))
</script>

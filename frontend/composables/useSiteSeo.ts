export function useSiteSeo() {
  const config = useRuntimeConfig()

  const siteName = 'Wohnort-Kompass'
  const organizationName = 'OK Lab Flensburg'
  const siteDescription =
    'Wohnort-Kompass vergleicht Regionen in Deutschland anhand offener Daten zu Klima, Luftqualität, Sicherheit, Demografie, Alltagsnähe und ÖPNV.'
  const siteLocale = 'de_DE'

  const normalizedSiteUrl = computed(() => String(config.public.siteUrl || '').replace(/\/+$/, ''))

  const absoluteUrl = (path = '/') => {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    return `${normalizedSiteUrl.value}${normalizedPath}`
  }

  return {
    siteName,
    organizationName,
    siteDescription,
    siteLocale,
    siteUrl: normalizedSiteUrl,
    absoluteUrl
  }
}

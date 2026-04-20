type RegionListItem = {
  slug: string
}

const rankingScopes = [
  'deutschland',
  'schleswig-holstein',
  'hamburg',
  'niedersachsen',
  'bremen',
  'nordrhein-westfalen',
  'hessen',
  'rheinland-pfalz',
  'baden-wuerttemberg',
  'bayern',
  'saarland',
  'berlin',
  'brandenburg',
  'mecklenburg-vorpommern',
  'sachsen',
  'sachsen-anhalt',
  'thueringen'
]

const rankingCategories = ['climate', 'air', 'safety', 'demographics', 'amenities', 'landuse', 'oepnv']

type RegionListResponse = {
  items: RegionListItem[]
}

type SitemapUrl = {
  loc: string
  changefreq?: string
  priority?: string
  lastmod?: string
}

function escapeXml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function toAbsoluteUrl(base: string, path: string) {
  const normalizedBase = base.replace(/\/+$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const siteUrl = String(config.public.siteUrl || '').replace(/\/+$/, '')
  const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')
  const today = new Date().toISOString().slice(0, 10)

  const urls: SitemapUrl[] = [
    { loc: toAbsoluteUrl(siteUrl, '/'), changefreq: 'weekly', priority: '1.0', lastmod: today },
    { loc: toAbsoluteUrl(siteUrl, '/finder'), changefreq: 'weekly', priority: '0.9', lastmod: today },
    { loc: toAbsoluteUrl(siteUrl, '/methodik'), changefreq: 'monthly', priority: '0.7', lastmod: today }
  ]

  for (const scope of rankingScopes) {
    for (const category of rankingCategories) {
      urls.push({
        loc: toAbsoluteUrl(siteUrl, `/top-100/${scope}/${category}`),
        changefreq: 'weekly',
        priority: '0.6',
        lastmod: today
      })
    }
  }

  const regionsEndpoint = apiBase.startsWith('http') ? `${apiBase}/regions` : toAbsoluteUrl(siteUrl, `${apiBase}/regions`)

  try {
    const response = await $fetch<RegionListResponse>(regionsEndpoint)
    for (const region of response.items) {
      if (!region.slug) {
        continue
      }
      urls.push({
        loc: toAbsoluteUrl(siteUrl, `/region/${region.slug}`),
        changefreq: 'weekly',
        priority: '0.8',
        lastmod: today
      })
    }
  } catch {
    // Keep the sitemap available even if the backend region list is unavailable.
  }

  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls.map((url) => {
      const parts = ['  <url>', `    <loc>${escapeXml(url.loc)}</loc>`]
      if (url.lastmod) {
        parts.push(`    <lastmod>${url.lastmod}</lastmod>`)
      }
      if (url.changefreq) {
        parts.push(`    <changefreq>${url.changefreq}</changefreq>`)
      }
      if (url.priority) {
        parts.push(`    <priority>${url.priority}</priority>`)
      }
      parts.push('  </url>')
      return parts.join('\n')
    }),
    '</urlset>'
  ].join('\n')

  setHeader(event, 'content-type', 'application/xml; charset=utf-8')
  return body
})

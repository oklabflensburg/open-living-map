export default defineEventHandler((event) => {
  const config = useRuntimeConfig(event)
  const siteUrl = String(config.public.siteUrl || '').replace(/\/+$/, '')

  const body = [
    'User-agent: *',
    'Allow: /',
    'Disallow: /compare',
    'Disallow: /results',
    `Sitemap: ${siteUrl}/sitemap.xml`
  ].join('\n')

  setHeader(event, 'content-type', 'text/plain; charset=utf-8')
  return body
})

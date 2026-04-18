export default defineNuxtConfig({
  compatibilityDate: '2026-04-13',
  devtools: { enabled: true },
  modules: ['@pinia/nuxt', '@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css', 'leaflet/dist/leaflet.css'],
  app: {
    head: {
      htmlAttrs: {
        lang: 'de'
      },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#1d4ed8' }
      ]
    }
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'https://wohnortkompass.oklabflensburg.de'
    }
  },
  typescript: {
    strict: true,
    typeCheck: false
  }
})

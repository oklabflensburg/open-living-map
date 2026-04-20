import process from 'node:process'

export default defineNuxtConfig({
  compatibilityDate: '2026-04-13',
  devtools: { enabled: process.env.NODE_ENV !== 'production' },
  modules: ['@pinia/nuxt', '@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css', 'leaflet/dist/leaflet.css'],
  experimental: {
    appManifest: false
  },
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
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'https://wohnortkompass.oklabflensburg.de',
      repoUrl: process.env.NUXT_PUBLIC_REPO_URL || 'https://github.com/oklabflensburg/wohnortkompass',
      legalName: process.env.NUXT_PUBLIC_LEGAL_NAME || '',
      legalRepresentative: process.env.NUXT_PUBLIC_LEGAL_REPRESENTATIVE || '',
      legalStreet: process.env.NUXT_PUBLIC_LEGAL_STREET || '',
      legalPostalCode: process.env.NUXT_PUBLIC_LEGAL_POSTAL_CODE || '',
      legalCity: process.env.NUXT_PUBLIC_LEGAL_CITY || '',
      legalCountry: process.env.NUXT_PUBLIC_LEGAL_COUNTRY || 'Deutschland',
      legalEmail: process.env.NUXT_PUBLIC_LEGAL_EMAIL || '',
      legalPhone: process.env.NUXT_PUBLIC_LEGAL_PHONE || '',
      legalVatId: process.env.NUXT_PUBLIC_LEGAL_VAT_ID || '',
      privacyController: process.env.NUXT_PUBLIC_PRIVACY_CONTROLLER || '',
      privacyHostingProvider: process.env.NUXT_PUBLIC_PRIVACY_HOSTING_PROVIDER || '',
      privacyHostingLocation: process.env.NUXT_PUBLIC_PRIVACY_HOSTING_LOCATION || '',
      privacyHostingPolicyUrl: process.env.NUXT_PUBLIC_PRIVACY_HOSTING_POLICY_URL || ''
    }
  },
  typescript: {
    strict: true,
    typeCheck: process.env.CI === 'true' || process.env.NODE_ENV === 'production'
  }
})

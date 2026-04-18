export function useLegalConfig() {
  const config = useRuntimeConfig()

  const legal = computed(() => ({
    name: String(config.public.legalName || ''),
    representative: String(config.public.legalRepresentative || ''),
    street: String(config.public.legalStreet || ''),
    postalCode: String(config.public.legalPostalCode || ''),
    city: String(config.public.legalCity || ''),
    country: String(config.public.legalCountry || 'Deutschland'),
    email: String(config.public.legalEmail || ''),
    phone: String(config.public.legalPhone || ''),
    vatId: String(config.public.legalVatId || ''),
    privacyController: String(config.public.privacyController || config.public.legalName || ''),
    hostingProvider: String(config.public.privacyHostingProvider || ''),
    hostingLocation: String(config.public.privacyHostingLocation || ''),
    hostingPolicyUrl: String(config.public.privacyHostingPolicyUrl || ''),
    repoUrl: String(config.public.repoUrl || '')
  }))

  const postalLine = computed(() => {
    const parts = [legal.value.postalCode, legal.value.city].filter(Boolean)
    return parts.join(' ')
  })

  return {
    legal,
    postalLine
  }
}

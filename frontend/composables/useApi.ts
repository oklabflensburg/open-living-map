export function useApi() {
  const config = useRuntimeConfig()
  const { startRequest, finishRequest } = useApiLoading()

  const apiFetch = async <T>(path: string, options?: Parameters<typeof $fetch<T>>[1]): Promise<T> => {
    if (import.meta.client) {
      startRequest()
    }

    try {
      return await $fetch(`${config.public.apiBase}${path}`, options) as T
    } finally {
      if (import.meta.client) {
        finishRequest()
      }
    }
  }

  return { apiFetch }
}

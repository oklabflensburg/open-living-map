export function useApi() {
  const config = useRuntimeConfig()

  const apiFetch = async <T>(path: string, options?: Parameters<typeof $fetch<T>>[1]): Promise<T> => {
    return await $fetch(`${config.public.apiBase}${path}`, options) as T
  }

  return { apiFetch }
}

export function useApiLoading() {
  const activeRequests = useState('api-loading-active-requests', () => 0)

  const isLoading = computed(() => activeRequests.value > 0)

  function startRequest() {
    activeRequests.value += 1
  }

  function finishRequest() {
    activeRequests.value = Math.max(0, activeRequests.value - 1)
  }

  return {
    activeRequests,
    isLoading,
    startRequest,
    finishRequest
  }
}
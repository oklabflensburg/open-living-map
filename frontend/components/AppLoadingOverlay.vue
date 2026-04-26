<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="showOverlay"
      class="pointer-events-none fixed inset-0 z-[1400] flex items-center justify-center bg-slate-950/12 backdrop-blur-[2px]"
      aria-live="polite"
      aria-busy="true"
    >
      <div class="flex items-center gap-4 rounded-2xl border border-white/70 bg-white px-5 py-4 shadow-[0_24px_80px_rgba(15,23,42,0.18)] ring-1 ring-slate-200/70">
        <AppLogo class="h-14 w-14" />
        <div>
          <p class="text-sm font-semibold text-slate-900">Daten werden geladen</p>
          <div class="mt-1 flex items-center gap-2 text-xs text-slate-500">
            <span class="h-4 w-4 animate-spin rounded-full border-2 border-sky-200 border-t-sky-600" />
            <span>Einen Moment bitte.</span>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
const { isLoading } = useApiLoading()

const showOverlay = ref(false)
let showTimer: ReturnType<typeof setTimeout> | null = null

watch(
  isLoading,
  (loading) => {
    if (showTimer) {
      clearTimeout(showTimer)
      showTimer = null
    }

    if (loading) {
      showTimer = setTimeout(() => {
        showOverlay.value = true
      }, 120)
      return
    }

    showOverlay.value = false
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  if (showTimer) {
    clearTimeout(showTimer)
  }
})
</script>
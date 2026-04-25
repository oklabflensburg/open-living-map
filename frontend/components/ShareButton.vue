<template>
  <button
    type="button"
    class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-900"
    @click="share"
  >
    {{ buttonLabel }}
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{
  path: string
  label?: string
  shareTitle?: string
  shareText?: string
}>()

const copied = ref(false)
const failed = ref(false)

const buttonLabel = computed(() => {
  if (copied.value) {
    return 'Link kopiert'
  }
  if (failed.value) {
    return 'Kopieren fehlgeschlagen'
  }
  return props.label || 'Link kopieren'
})

async function share() {
  const url = new URL(props.path, window.location.origin).toString()

  try {
    if (navigator.share) {
      await navigator.share({
        title: props.shareTitle || document.title,
        text: props.shareText,
        url
      })
      return
    }

    await navigator.clipboard.writeText(url)
    copied.value = true
    window.setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch {
    failed.value = true
    window.setTimeout(() => {
      failed.value = false
    }, 2200)
  }
}
</script>

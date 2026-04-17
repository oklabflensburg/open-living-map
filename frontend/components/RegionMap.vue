<template>
  <ClientOnly>
    <div ref="container" class="h-80 w-full rounded-xl border border-slate-200" />
  </ClientOnly>
</template>

<script setup lang="ts">
import type { RecommendationItem } from '~/types/api'

const props = defineProps<{ items: RecommendationItem[] }>()
const router = useRouter()
const container = ref<HTMLElement | null>(null)
let LLeaflet: typeof import('leaflet') | null = null
let map: import('leaflet').Map | null = null
let layer: import('leaflet').LayerGroup | null = null
let markerIcon: import('leaflet').Icon | null = null

onMounted(async () => {
  LLeaflet = await import('leaflet')
  if (!container.value) {
    return
  }

  markerIcon = LLeaflet.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41]
  })

  map = LLeaflet.map(container.value).setView([51.2, 10.4], 6)
  LLeaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  layer = LLeaflet.layerGroup().addTo(map)
  renderMarkers()
})

function renderMarkers() {
  if (!LLeaflet || !map || !layer || !markerIcon) {
    return
  }
  layer.clearLayers()

  const points = props.items.filter((item) => item.centroid_lat != null && item.centroid_lon != null)
  points.forEach((item) => {
    const marker = LLeaflet.marker([item.centroid_lat as number, item.centroid_lon as number], { icon: markerIcon })
    marker.bindPopup(`${item.name} (${item.score_total.toFixed(1)})`)
    marker.on('click', () => router.push(`/region/${item.slug || item.ars}`))
    marker.addTo(layer as import('leaflet').LayerGroup)
  })

  if (points.length > 0) {
    const bounds = LLeaflet.latLngBounds(
      points.map((item) => [item.centroid_lat as number, item.centroid_lon as number])
    )
    map.fitBounds(bounds.pad(0.2))
  }
}

watch(
  () => props.items,
  () => renderMarkers(),
  { deep: true }
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

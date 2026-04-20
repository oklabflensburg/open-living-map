<template>
  <ClientOnly>
    <div class="relative">
      <div ref="container" class="h-80 w-full rounded-xl border border-slate-200" />
      <div
        v-if="showLoadingOverlay"
        class="absolute inset-0 z-10 flex items-center justify-center rounded-xl border border-slate-200 bg-white/85 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm">
          <span class="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
          Kartendaten werden geladen
        </div>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup lang="ts">
import type { GeoJsonFeatureCollection, RecommendationItem } from '~/types/api'

const props = defineProps<{
  items: RecommendationItem[]
  stateBoundaries?: GeoJsonFeatureCollection | null
  loading?: boolean
}>()
const router = useRouter()
const container = ref<HTMLElement | null>(null)
const tilesLoading = ref(true)
let LLeaflet: typeof import('leaflet') | null = null
let map: import('leaflet').Map | null = null
let stateLayer: import('leaflet').GeoJSON | null = null
let layer: import('leaflet').LayerGroup | null = null
let markerIcon: import('leaflet').Icon | null = null

const showLoadingOverlay = computed(() => props.loading || tilesLoading.value)

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
  const tileLayer = LLeaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  })
  tileLayer.on('loading', () => {
    tilesLoading.value = true
  })
  tileLayer.on('load', () => {
    tilesLoading.value = false
  })
  tileLayer.addTo(map)

  layer = LLeaflet.layerGroup().addTo(map)
  renderStateBoundaries()
  renderMarkers()
})

function renderStateBoundaries() {
  if (!LLeaflet || !map) {
    return
  }

  stateLayer?.remove()
  stateLayer = null

  const featureCollection = props.stateBoundaries
  if (!featureCollection?.features?.length) {
    return
  }

  stateLayer = LLeaflet.geoJSON(featureCollection as never, {
    style: {
      color: '#2563eb',
      weight: 2,
      fillColor: '#93c5fd',
      fillOpacity: 0.08
    },
    onEachFeature(feature, itemLayer) {
      const properties = (feature.properties || {}) as Record<string, unknown>
      const stateName = typeof properties.state_name === 'string' ? properties.state_name : 'Bundesland'
      itemLayer.bindPopup(stateName)
    }
  }).addTo(map)
}

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
  } else if (stateLayer) {
    map.fitBounds(stateLayer.getBounds().pad(0.08))
  }
}

watch(
  () => props.items,
  () => renderMarkers(),
  { deep: true }
)

watch(
  () => props.stateBoundaries,
  () => {
    renderStateBoundaries()
    renderMarkers()
  },
  { deep: true }
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

<template>
  <ClientOnly>
    <div ref="container" class="h-96 w-full rounded-xl border border-slate-200" />
  </ClientOnly>
</template>

<script setup lang="ts">
const props = defineProps<{
  geometry: Record<string, unknown> | null
  name: string
  centroidLat: number | null
  centroidLon: number | null
  overlayPois?: Record<string, unknown> | null
  selectedOverlayLabel?: string | null
}>()

const container = ref<HTMLElement | null>(null)
let LLeaflet: typeof import('leaflet') | null = null
let map: import('leaflet').Map | null = null
let boundaryLayer: import('leaflet').GeoJSON | null = null
let poiLayer: import('leaflet').GeoJSON | null = null

onMounted(async () => {
  LLeaflet = await import('leaflet')
  if (!container.value) {
    return
  }

  map = LLeaflet.map(container.value).setView([props.centroidLat || 51.2, props.centroidLon || 10.4], 11)
  LLeaflet.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  renderBoundary()
  renderPois()
})

function renderBoundary() {
  if (!LLeaflet || !map) {
    return
  }

  boundaryLayer?.remove()
  boundaryLayer = null

  if (!props.geometry) {
    if (props.centroidLat != null && props.centroidLon != null) {
      map.setView([props.centroidLat, props.centroidLon], 11)
    }
    return
  }

  boundaryLayer = LLeaflet.geoJSON(props.geometry as never, {
    style: {
      color: '#0369a1',
      fillColor: '#38bdf8',
      fillOpacity: 0.22,
      weight: 3
    }
  }).bindPopup(props.name)

  boundaryLayer.addTo(map)
  map.fitBounds(boundaryLayer.getBounds().pad(0.08))
}

function renderPois() {
  if (!LLeaflet || !map) {
    return
  }

  poiLayer?.remove()
  poiLayer = null

  const featureCollection = props.overlayPois as { features?: unknown[] } | null
  if (!featureCollection?.features?.length) {
    return
  }

  poiLayer = LLeaflet.geoJSON(props.overlayPois as never, {
    pointToLayer(_feature, latlng) {
      return LLeaflet!.circleMarker(latlng, {
        radius: 6,
        color: '#b45309',
        weight: 2,
        fillColor: '#f59e0b',
        fillOpacity: 0.9
      })
    },
    onEachFeature(feature, layer) {
      const properties = (feature.properties || {}) as Record<string, unknown>
      const label = props.selectedOverlayLabel || 'POI'
      const name = typeof properties.name === 'string' && properties.name ? properties.name : null
      const year = typeof properties.year === 'number' ? String(properties.year) : null
      const detail = name || year || ''
      layer.bindPopup(detail ? `<strong>${label}</strong><br>${detail}` : `<strong>${label}</strong>`)
    }
  })

  poiLayer.addTo(map)
}

watch(
  () => props.geometry,
  () => renderBoundary(),
  { deep: true }
)

watch(
  () => props.overlayPois,
  () => renderPois(),
  { deep: true }
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

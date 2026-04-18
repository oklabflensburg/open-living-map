<template>
  <ClientOnly>
    <div ref="container" class="h-96 w-full rounded-xl border border-slate-200" />
  </ClientOnly>
</template>

<script setup lang="ts">
type AirStationMapInfo = {
  indicator_key: string
  label: string
  station_id: string
  station_code: string | null
  station_name: string
  latitude: number | null
  longitude: number | null
  station_page_url: string | null
  measures_url: string
}

const props = defineProps<{
  geometry: Record<string, unknown> | null
  name: string
  centroidLat: number | null
  centroidLon: number | null
  overlayPois?: Record<string, unknown> | null
  selectedOverlayLabel?: string | null
  airStations?: AirStationMapInfo[]
  selectedAirStationId?: string | null
}>()

const container = ref<HTMLElement | null>(null)
let LLeaflet: typeof import('leaflet') | null = null
let map: import('leaflet').Map | null = null
let boundaryLayer: import('leaflet').GeoJSON | null = null
let poiLayer: import('leaflet').GeoJSON | null = null
let airStationLayer: import('leaflet').LayerGroup | null = null
let airStationMarkers = new Map<string, import('leaflet').CircleMarker>()

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
  renderAirStations()
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

function renderAirStations() {
  if (!LLeaflet || !map) {
    return
  }

  airStationLayer?.remove()
  airStationLayer = null
  airStationMarkers = new Map()

  const stations = (props.airStations || []).filter(
    (station) => station.latitude != null && station.longitude != null
  )
  if (!stations.length) {
    return
  }

  const grouped = new Map<
    string,
    {
      station_name: string
      station_code: string | null
      station_id: string
      latitude: number
      longitude: number
      station_page_url: string | null
      measures_url: string
      labels: string[]
    }
  >()

  for (const station of stations) {
    const key = station.station_id
    const existing = grouped.get(key)
    if (existing) {
      existing.labels.push(station.label)
      continue
    }
    grouped.set(key, {
      station_name: station.station_name,
      station_code: station.station_code,
      station_id: station.station_id,
      latitude: station.latitude!,
      longitude: station.longitude!,
      station_page_url: station.station_page_url,
      measures_url: station.measures_url,
      labels: [station.label]
    })
  }

  airStationLayer = LLeaflet.layerGroup(
    Array.from(grouped.values()).map((station) => {
      const marker = LLeaflet!.circleMarker([station.latitude, station.longitude], {
        radius: 7,
        color: '#0369a1',
        weight: 2,
        fillColor: '#0ea5e9',
        fillOpacity: 0.9
      })

      const labels = station.labels.join(', ')
      const stationUrl = station.station_page_url || station.measures_url
      const codeText = station.station_code ? ` (${station.station_code})` : ''
      const popupHtml = [
        `<strong>${station.station_name}${codeText}</strong>`,
        labels ? `<br>Messwerte: ${labels}` : '',
        `<br>Koordinaten: ${station.latitude.toFixed(5)}, ${station.longitude.toFixed(5)}`,
        `<br><a href="${stationUrl}" target="_blank" rel="noreferrer">Station öffnen</a>`
      ].join('')

      marker.bindPopup(popupHtml)
      airStationMarkers.set(station.station_id, marker)
      return marker
    })
  )

  airStationLayer.addTo(map)
  focusSelectedAirStation()
}

function focusSelectedAirStation() {
  if (!map || !props.selectedAirStationId) {
    return
  }

  const marker = airStationMarkers.get(props.selectedAirStationId)
  if (!marker) {
    return
  }

  const target = marker.getLatLng()
  map.flyTo(target, Math.max(map.getZoom(), 12), {
    duration: 0.6
  })
  marker.openPopup()
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

watch(
  () => props.airStations,
  () => renderAirStations(),
  { deep: true }
)

watch(
  () => props.selectedAirStationId,
  () => focusSelectedAirStation()
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>

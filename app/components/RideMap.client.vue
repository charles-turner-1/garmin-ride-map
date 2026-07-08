<script setup lang="ts">
import { Map as MapLibreMap, LngLatBounds } from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import type { FeatureCollection, LineString } from 'geojson'
import 'maplibre-gl/dist/maplibre-gl.css'

type RideCollection = FeatureCollection<LineString>

const STYLES = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark'
}

const SOURCE_ID = 'rides'

const container = ref<HTMLDivElement>()
const colorMode = useColorMode()
const { app } = useRuntimeConfig()

let map: MapLibreMap | undefined
let rides: RideCollection | undefined

function styleUrl() {
  return colorMode.value === 'dark' ? STYLES.dark : STYLES.light
}

// Re-adds the ride source + layers. Called on first load and after any basemap
// style swap (setStyle wipes custom sources/layers, so we must re-add them).
function addRideLayers() {
  if (!map || !rides) return

  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, { type: 'geojson', data: rides })
  } else {
    (map.getSource(SOURCE_ID) as GeoJSONSource).setData(rides)
  }

  // Wide, faint underlay so overlapping rides bloom into a heatmap glow.
  if (!map.getLayer('rides-glow')) {
    map.addLayer({
      id: 'rides-glow',
      type: 'line',
      source: SOURCE_ID,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': '#f97316',
        'line-width': 6,
        'line-opacity': 0.12,
        'line-blur': 3
      }
    })
  }

  // Crisp core line. Low opacity means frequently-ridden roads accumulate.
  if (!map.getLayer('rides-line')) {
    map.addLayer({
      id: 'rides-line',
      type: 'line',
      source: SOURCE_ID,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': '#fb923c',
        'line-width': 2,
        'line-opacity': 0.5
      }
    })
  }
}

function fitToRides() {
  if (!map || !rides || rides.features.length === 0) return
  const bounds = new LngLatBounds()
  for (const feature of rides.features) {
    for (const coord of feature.geometry.coordinates) {
      bounds.extend(coord as [number, number])
    }
  }
  if (!bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 64, duration: 0 })
  }
}

onMounted(async () => {
  // Wait a tick so the template ref is bound: this is a client-only component
  // rendered inside the async (Suspense) page, where the ref can still be
  // empty on the first onMounted pass.
  await nextTick()
  if (!container.value) return

  rides = await $fetch<RideCollection>(`${app.baseURL}data/rides.geojson`)

  map = new MapLibreMap({
    container: container.value,
    style: styleUrl(),
    center: [115.78, -32.03], // Perth metro: Yanchep (N) to Mandurah (S)
    zoom: 8.3,
    attributionControl: { compact: true }
  })

  map.on('load', () => {
    addRideLayers()
    fitToRides()
  })

  // Swap basemap when the user toggles light/dark; re-add layers once ready.
  watch(() => colorMode.value, () => {
    if (!map) return
    map.setStyle(styleUrl())
    map.once('style.load', addRideLayers)
  })
})

onBeforeUnmount(() => {
  map?.remove()
  map = undefined
})
</script>

<template>
  <div
    ref="container"
    class="size-full"
  />
</template>

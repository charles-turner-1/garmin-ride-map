<script setup lang="ts">
import { Map as MapLibreMap } from 'maplibre-gl'
import type { GeoJSONSource, ExpressionSpecification } from 'maplibre-gl'
import type { FeatureCollection, LineString } from 'geojson'
import 'maplibre-gl/dist/maplibre-gl.css'

interface RideProperties {
  id: string
  date: string
  distanceKm: number
  type: string
  // Numeric recency key (epoch ms) injected client-side after fetch (see onMounted).
  t?: number
}

type RideCollection = FeatureCollection<LineString, RideProperties>

const STYLES = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark'
}

const SOURCE_ID = 'rides'
const DEFAULT_VIEW_BOUNDS: [[number, number], [number, number]] = [
  [115.50, -32.90], // Southwest: just south/west of Waroona.
  [116.20, -31.30] // Northeast: just north/east of Gingin.
]

const emit = defineEmits<{ range: [{ oldest: string, newest: string }] }>()

const container = ref<HTMLDivElement>()
const colorMode = useColorMode()
const { app } = useRuntimeConfig()

let map: MapLibreMap | undefined
let rides: RideCollection | undefined

// Data-driven colour: interpolate each ride's recency key `t` across the shared
// blue -> mauve -> orange ramp. Domain is the oldest..newest span of the data.
// Falls back to a solid newest colour when every ride shares one date.
let colorExpr: ExpressionSpecification | string = RIDE_RAMP[RIDE_RAMP.length - 1]!.color

function buildColorExpr(min: number, max: number) {
  if (!(max > min)) {
    colorExpr = RIDE_RAMP[RIDE_RAMP.length - 1]!.color
    return
  }
  const stops = RIDE_RAMP.flatMap(s => [min + (max - min) * s.pos, s.color])
  colorExpr = ['interpolate', ['linear'], ['get', 't'], ...stops] as ExpressionSpecification
}

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
        'line-color': colorExpr,
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
        'line-color': colorExpr,
        'line-width': 2,
        'line-opacity': 0.65
      }
    })
  }
}

onMounted(async () => {
  // Wait a tick so the template ref is bound: this is a client-only component
  // rendered inside the async (Suspense) page, where the ref can still be
  // empty on the first onMounted pass.
  await nextTick()
  if (!container.value) return

  // Force JSON parsing: static hosts (GitHub Pages, plain file servers) may
  // serve .geojson as octet-stream, which $fetch would otherwise return as text.
  rides = await $fetch<RideCollection>(`${app.baseURL}data/rides.geojson`, {
    responseType: 'json'
  })

  // Derive a numeric recency key from each ride's `date` (YYYY-MM-DD), build the
  // colour ramp over the oldest..newest span, and sort so newer rides draw on top.
  const features = rides.features
  if (features.length) {
    for (const f of features) {
      f.properties.t = Date.parse(f.properties.date)
    }
    features.sort((a, b) => (a.properties.t ?? 0) - (b.properties.t ?? 0))
    const oldest = features[0]!.properties
    const newest = features[features.length - 1]!.properties
    buildColorExpr(oldest.t ?? 0, newest.t ?? 0)
    emit('range', { oldest: oldest.date, newest: newest.date })
  }

  map = new MapLibreMap({
    container: container.value,
    style: styleUrl(),
    bounds: DEFAULT_VIEW_BOUNDS,
    fitBoundsOptions: { padding: 48 },
    attributionControl: { compact: true }
  })

  map.on('load', () => {
    addRideLayers()
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

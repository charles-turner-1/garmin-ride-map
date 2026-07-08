<script setup lang="ts">
interface Manifest {
  count: number
  lastRun: string
}

const { app } = useRuntimeConfig()
// Fetch client-side only: an SSR $fetch to a static /public JSON file 500s
// during prerender (it hits the SPA fallback route, not the asset handler).
const { data: manifest } = await useAsyncData(
  'manifest',
  () => $fetch<Manifest>(`${app.baseURL}data/manifest.json`, { responseType: 'json' }),
  { server: false }
)

const lastRun = computed(() => {
  if (!manifest.value?.lastRun) return null
  return formatDate(manifest.value.lastRun)
})

// Oldest/newest ride dates, emitted by RideMap once the geojson loads.
const range = ref<{ oldest: string, newest: string } | null>(null)

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}
</script>

<template>
  <div class="fixed inset-0">
    <RideMap @range="range = $event" />

    <UCard class="absolute top-4 left-4 z-10 backdrop-blur">
      <div class="flex items-center gap-2">
        <UIcon
          name="i-lucide-bike"
          class="size-5 text-primary"
        />
        <h1 class="font-semibold">
          Ride Map
        </h1>
        <UColorModeButton class="-my-1" />
      </div>

      <p class="mt-2 text-sm text-muted">
        <span class="font-medium text-highlighted">{{ manifest?.count ?? 0 }}</span> rides
        <template v-if="lastRun">
          · updated {{ lastRun }}
        </template>
      </p>
    </UCard>

    <UCard
      v-if="range"
      class="absolute bottom-4 left-4 z-10 backdrop-blur"
    >
      <p class="text-xs font-medium text-muted">
        Ride date
      </p>
      <div
        class="mt-1.5 h-2 w-40 rounded"
        :style="{ background: rideRampCss() }"
      />
      <div class="mt-1 flex justify-between gap-4 text-xs text-muted tabular-nums">
        <span>{{ formatDate(range.oldest) }}</span>
        <span>{{ formatDate(range.newest) }}</span>
      </div>
    </UCard>
  </div>
</template>

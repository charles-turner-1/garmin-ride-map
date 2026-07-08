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
  () => $fetch<Manifest>(`${app.baseURL}data/manifest.json`),
  { server: false }
)

const lastRun = computed(() => {
  if (!manifest.value?.lastRun) return null
  return new Date(manifest.value.lastRun).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
})
</script>

<template>
  <div class="fixed inset-0">
    <RideMap />

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
  </div>
</template>

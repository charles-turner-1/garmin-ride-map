<script setup>
// Prefix with baseURL so the favicon resolves under a project Pages subpath.
const { app } = useRuntimeConfig()

useHead({
  meta: [
    { name: 'viewport', content: 'width=device-width, initial-scale=1' }
  ],
  link: [
    { rel: 'icon', href: `${app.baseURL}favicon.ico` }
  ],
  htmlAttrs: {
    lang: 'en'
  }
})

const title = 'Ride Map'
const description = 'Every cycle ride from my Garmin history, mapped.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  twitterCard: 'summary_large_image'
})
</script>

<template>
  <UApp>
    <NuxtPage />
  </UApp>
</template>

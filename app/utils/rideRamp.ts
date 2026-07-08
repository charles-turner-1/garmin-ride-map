// Single source of truth for the "colour by recency" ramp so the MapLibre line
// expression (RideMap.client.vue) and the legend gradient (index.vue) stay in sync.
//
// gist_ncar-flavoured spectrum, oldest -> newest: blue -> teal -> green -> gold ->
// orange -> red -> magenta. A long, multi-hue ramp so nearby dates stay
// distinguishable; each hop is between neighbouring hues so transitions never mud
// out to grey. Greens and yellows are pulled darker than a naive spectrum so every
// stop clears >=3:1 mark-contrast against both basemaps (positron light and dark) --
// the ramp is basemap-independent and old rides stay as visible as recent ones.
export const RIDE_RAMP = [
  { pos: 0, color: '#1f6fd0' }, // oldest (blue)
  { pos: 1 / 6, color: '#0f8a8a' }, // teal
  { pos: 2 / 6, color: '#1f8f3f' }, // green
  { pos: 3 / 6, color: '#a67c08' }, // gold
  { pos: 4 / 6, color: '#d1490b' }, // orange
  { pos: 5 / 6, color: '#c02f2f' }, // red
  { pos: 1, color: '#cc2f8a' } // newest (magenta)
] as const

// Left-to-right CSS gradient (blue -> orange) for the legend bar.
export const rideRampCss = () =>
  `linear-gradient(to right, ${RIDE_RAMP.map(s => `${s.color} ${s.pos * 100}%`).join(', ')})`

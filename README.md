# garmin-ride-map

> [!WARNING]
> This was vibe coded. If you plan on using it, please don't blame me if this causes
> literally anything at all bad to happen to you, your computer, or the secrecy of
> your environment variables. AFAIK it's fine but I haven't bothered to read the code
> yet. Maybe one day I will....

A dead-simple personal map of every cycle ride from my Garmin history — drawn as
overlapping translucent route lines (Strava-heatmap style) so I can see where
I have and haven't been.

Built with [Nuxt 4](https://nuxt.com) + [Nuxt UI](https://ui.nuxt.com) and
[MapLibre GL](https://maplibre.org), on the keyless
[OpenFreeMap](https://openfreemap.org) basemap. A small Python service pulls new
rides from Garmin on a schedule and commits the data, which auto-deploys to
GitHub Pages.

## How it works

```
Garmin Connect ──(ingest/garmin_ingest.py, scheduled)──▶ public/data/rides.geojson
                                                                  │
                                          GitHub Actions build ───▶ GitHub Pages
                                                                  │
                                             MapLibre map (app/) ◀─┘
```

- **`app/`** — the map. `RideMap.client.vue` renders the routes; `pages/index.vue`
  is a full-screen map with a small info card.
- **`ingest/`** — the Python service that fetches rides, simplifies the GPS
  tracks, and clips points near home for privacy. See [`ingest/README.md`](ingest/README.md).
- **`public/data/`** — the committed `rides.geojson` + `manifest.json` the map reads.
- **`.github/workflows/`** — `deploy` (build + publish on push) and `ingest`
  (scheduled pull → commit → redeploy).

## Local development

```bash
pnpm install
pnpm dev            # http://localhost:3000
```

The repo ships with demo rides around Perth so the map works before any Garmin
data is wired up. Lint/typecheck: `pnpm lint`, `pnpm typecheck`.

## Deployment (one-time setup)

The site deploys to `https://charles-turner-1.github.io/garmin-ride-map/`.

1. **Enable Pages:** repo *Settings → Pages → Source = GitHub Actions*.
2. **Add repo secrets** (*Settings → Secrets and variables → Actions*):
   - `GARMIN_TOKENSTORE_B64` — from `python ingest/save_token.py`
   - `PRIVACY_CENTER` — your home point as `lat,lng` (kept out of the repo)
3. Push to `main` — the `deploy` workflow builds and publishes automatically.

> The base path is `/garmin-ride-map/` (set in `deploy-pages.yml`). If you rename
> the repo or use a custom domain, update `NUXT_APP_BASE_URL` there.

## Seeding real ride data

Needs your Garmin login + MFA once, locally:

```bash
cd ingest
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # then set PRIVACY_CENTER (your real home point)
python save_token.py                 # paste MFA code → copy token into ingest/.env
python garmin_ingest.py              # pulls your rides; replaces the demo data
```

Commit the updated `public/data/` and push. After that the scheduled `ingest`
workflow keeps it fresh daily using the repo secrets.

Defaults: all cycling activities, last 4 years, 500 m privacy radius. Tune via
env vars — e.g. set `RIDE_TYPES=road_biking` to narrow (see
[`ingest/README.md`](ingest/README.md)).

## Notes

- The ingestion uses the **unofficial** Garmin Connect API — against Garmin's ToS
  and liable to break; fine for a personal project.
- Ride start/end points are clipped and jittered near home before anything is
  committed, so the public repo doesn't expose your address.

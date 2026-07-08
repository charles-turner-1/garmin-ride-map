# Garmin ingestion service

Pulls your cycling activities from Garmin Connect, extracts + simplifies the GPS
tracks, clips points near home for privacy, and writes them to
`../public/data/rides.geojson` (+ `manifest.json`) which the map reads.

Uses the unofficial [`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect)
API. This is against Garmin's ToS and can break when Garmin changes auth — fine
for a personal project, but don't rely on it.

## One-time setup

```bash
cd ingest
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env        # then edit .env
```

Generate a token (handles MFA), and paste the printed value into `.env`:

```bash
python save_token.py
# -> copy the GARMIN_TOKENSTORE_B64 line into ingest/.env
```

Also set your real home point in `.env` as `PRIVACY_CENTER=lat,lng` — this stays
local and is never committed. `.env.example` only holds placeholders.

## Run

```bash
python garmin_ingest.py
```

Incremental: activity ids already in `manifest.json` are skipped, so re-runs only
fetch new rides. The first real run also drops the `demo-*` seed rides.

## Config (`.env`)

| Var | Default | Meaning |
| --- | --- | --- |
| `GARMIN_TOKENSTORE_B64` | — | base64 token from `save_token.py` (required) |
| `PRIVACY_CENTER` | — | home point `lat,lng`; points within the radius are dropped |
| `PRIVACY_RADIUS_M` | `500` | privacy clip radius in metres |
| `PRIVACY_JITTER_M` | `200` | max random offset applied to exposed endpoints |
| `RIDE_TYPES` | _(blank)_ | comma-separated typeKeys to include; blank = any cycling activity (matched by parent type) |
| `SINCE_YEARS` | `4` | how many years of history to pull |
| `SIMPLIFY_TOLERANCE` | `0.0001` | Douglas–Peucker tolerance in degrees (~11 m) |

## CI

The scheduled GitHub workflow (Phase 3) sets these same variables from repo
secrets — `GARMIN_TOKENSTORE_B64` and `PRIVACY_CENTER` are the sensitive ones —
runs this script, commits any changed data, and redeploys the site.

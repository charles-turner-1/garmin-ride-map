"""Ingest Garmin cycling activities into public/data/rides.geojson.

Auth uses python-garminconnect with a base64 tokenstore (GARMIN_TOKENSTORE_B64),
so CI never needs your password or MFA. Generate the token once locally with
`python ingest/save_token.py` — see ingest/README.md.

Run:  python ingest/garmin_ingest.py
Config comes from environment variables (ingest/.env locally, GitHub secrets in
CI). See ingest/.env.example for the full list.
"""

from __future__ import annotations

import base64
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import gpxpy
from shapely.geometry import LineString

Coord = tuple[float, float]  # (lon, lat)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"
RIDES_PATH = DATA_DIR / "rides.geojson"
MANIFEST_PATH = DATA_DIR / "manifest.json"
ENV_PATH = Path(__file__).resolve().parent / ".env"

EARTH_RADIUS_M = 6371000.0
METERS_PER_DEG_LAT = 111320.0


# --- config / env -----------------------------------------------------------


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency). Real values live here locally and in
    GitHub secrets in CI; existing env vars always win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def parse_center(raw: Optional[str]) -> Optional[Coord]:
    """Parse 'lat,lng' -> (lon, lat), or None if unset/blank."""
    if not raw or not raw.strip():
        return None
    lat_s, lon_s = raw.split(",")
    return (float(lon_s), float(lat_s))


# --- geometry ----------------------------------------------------------------


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def jitter_point(lon: float, lat: float, max_m: float) -> Coord:
    """Offset a point by a random vector of up to max_m metres."""
    if max_m <= 0:
        return (lon, lat)
    r = random.uniform(0, max_m)
    theta = random.uniform(0, 2 * math.pi)
    dlat = (r * math.cos(theta)) / METERS_PER_DEG_LAT
    dlon = (r * math.sin(theta)) / (METERS_PER_DEG_LAT * math.cos(math.radians(lat)))
    return (lon + dlon, lat + dlat)


def clip_privacy(
    coords: list[Coord], center: Optional[Coord], radius_m: float, jitter_m: float
) -> list[Coord]:
    """Drop points within radius_m of home, then jitter the exposed endpoints so
    they don't trace a clean circle around the home location."""
    if not center or radius_m <= 0:
        return coords
    clon, clat = center
    kept = [
        (lon, lat)
        for lon, lat in coords
        if haversine_m(lon, lat, clon, clat) > radius_m
    ]
    if len(kept) < 2:
        return kept
    kept[0] = jitter_point(*kept[0], jitter_m)
    kept[-1] = jitter_point(*kept[-1], jitter_m)
    return kept


def simplify_coords(coords: list[Coord], tolerance: float) -> list[Coord]:
    """Douglas-Peucker simplify (~0.0001 deg ≈ 11 m) and round to shrink output."""
    if len(coords) < 2:
        return coords
    line = LineString(coords).simplify(tolerance, preserve_topology=False)
    return [(round(x, 5), round(y, 5)) for x, y in line.coords]


def extract_coords_from_gpx(raw: bytes | str) -> list[Coord]:
    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
    gpx = gpxpy.parse(text)
    coords: list[Coord] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                if pt.longitude is not None and pt.latitude is not None:
                    coords.append((pt.longitude, pt.latitude))
    return coords


# --- geojson store -----------------------------------------------------------


def build_feature(activity: dict, coords: list[Coord]) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "id": str(activity.get("activityId")),
            "date": (activity.get("startTimeLocal") or "")[:10],
            "distanceKm": round((activity.get("distance") or 0) / 1000, 1),
            "type": activity.get("activityType", {}).get("typeKey"),
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[lon, lat] for lon, lat in coords],
        },
    }


def load_existing() -> tuple[list[dict], set[str]]:
    """Return existing real ride features + the set of processed activity ids.
    Demo seed data (ids starting with 'demo-') is dropped on the first real run."""
    features: list[dict] = []
    if RIDES_PATH.exists():
        data = json.loads(RIDES_PATH.read_text())
        features = [
            f
            for f in data.get("features", [])
            if not str(f.get("properties", {}).get("id", "")).startswith("demo-")
        ]

    processed: set[str] = {str(f["properties"]["id"]) for f in features}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
        processed |= {
            pid
            for pid in manifest.get("processedIds", [])
            if not str(pid).startswith("demo-")
        }
    return features, processed


def write_output(features: list[dict], processed: set[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RIDES_PATH.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}) + "\n"
    )
    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "processedIds": sorted(processed),
                "count": len(features),
                "lastRun": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n"
    )


# --- main --------------------------------------------------------------------


def main() -> None:
    load_dotenv(ENV_PATH)

    token = os.environ.get("GARMIN_TOKENSTORE_B64", "").strip()
    if not token:
        sys.exit(
            "GARMIN_TOKENSTORE_B64 is not set. Run `python ingest/save_token.py` "
            "first, then put the value in ingest/.env (local) or a GitHub secret (CI). "
            "See ingest/README.md."
        )

    # Garmin has no single "cycling" flag — every cycling subtype (road_biking,
    # gravel_cycling, mountain_biking, virtual_ride, ...) shares parentTypeId 2.
    # Match on the parent so we grab *any* cycling activity without maintaining a
    # list. RIDE_TYPES (comma-separated typeKeys) can still narrow it if set.
    # ride_types = {t.strip() for t in os.environ.get("RIDE_TYPES", "").split(",") if t.strip()}
    CYCLING_TYPE_ID = 2
    since_years = int(os.environ.get("SINCE_YEARS", "4"))
    center = parse_center(os.environ.get("PRIVACY_CENTER"))
    radius_m = float(os.environ.get("PRIVACY_RADIUS_M", "500"))
    jitter_m = float(os.environ.get("PRIVACY_JITTER_M", "200"))
    tolerance = float(os.environ.get("SIMPLIFY_TOLERANCE", "0.0001"))

    from garminconnect import Garmin

    token_json = base64.b64decode(token).decode()
    client = Garmin()
    client.login(token_json)  # >512 chars -> loaded as a token, not a path

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * since_years + 1)
    print(f"Fetching all cycling activities {start} .. {end}")
    activities = client.get_activities_by_date(start.isoformat(), end.isoformat())
    print(f"Garmin returned {len(activities)} activities in range")

    features, processed = load_existing()
    new_count = 0
    for activity in activities:
        aid = str(activity.get("activityId"))
        if aid in processed:
            continue
        act_type = activity.get("activityType", {})
        if act_type.get("typeId") != CYCLING_TYPE_ID:
            continue

        try:
            raw = client.download_activity(
                aid, dl_fmt=Garmin.ActivityDownloadFormat.GPX
            )
            coords = extract_coords_from_gpx(raw)
        except Exception as exc:  # noqa: BLE001 - keep going on a single bad activity
            print(f"  skip {aid}: download/parse failed ({exc})")
            continue

        coords = clip_privacy(coords, center, radius_m, jitter_m)
        coords = simplify_coords(coords, tolerance)
        processed.add(
            aid
        )  # mark processed even if empty (indoor/no-GPS) so we don't retry
        if len(coords) < 2:
            continue

        features.append(build_feature(activity, coords))
        new_count += 1
        print(
            f"  + {aid} {activity.get('activityType', {}).get('typeKey')} {len(coords)} pts"
        )

    write_output(features, processed)
    print(f"Done. {new_count} new rides, {len(features)} total.")


if __name__ == "__main__":
    main()

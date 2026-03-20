"""Geopolitics data feeds -- GDELT events and DeepStateMap frontlines.

Ported from Shadowbroker geopolitics.py to async NEXUS patterns.
"""

from __future__ import annotations

import csv
import html as html_mod
import io
import re
import zipfile
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse

import aiohttp
import structlog

from nexus.utils.http_client import fetch_json, fetch_text

logger = structlog.get_logger("nexus.collectors.osint_feeds.geopolitics")

# ---------------------------------------------------------------------------
# URL / headline helpers
# ---------------------------------------------------------------------------


def _extract_domain(url: str) -> str:
    """Extract a clean source name from a URL, e.g. 'nytimes.com'."""
    try:
        host = urlparse(url).hostname or ""
        if host.startswith("www."):
            host = host[4:]
        return host
    except (ValueError, AttributeError):
        return url[:40]


def _is_gibberish(text: str) -> bool:
    """Detect if a URL segment is gibberish (hex IDs, UUIDs, numeric IDs)."""
    t = text.strip()
    if not t or len(t) < 5:
        return True
    if re.match(r"^\d+$", t):
        return True
    if re.match(
        r"^[0-9a-f]{8}[_-]?[0-9a-f]{4}[_-]?[0-9a-f]{4}[_-]?[0-9a-f]{4}[_-]?[0-9a-f]{12}$",
        t,
        re.I,
    ):
        return True
    alnum = re.sub(r"[^a-zA-Z0-9]", "", t)
    if alnum:
        hex_chars = sum(1 for c in alnum if c in "0123456789abcdefABCDEF")
        if hex_chars / len(alnum) > 0.4 and len(alnum) > 6:
            return True
        digits = sum(1 for c in alnum if c.isdigit())
        if digits / len(alnum) > 0.5:
            return True
    if "=" in t:
        return True
    return False


def _url_to_headline(url: str) -> str:
    """Extract a human-readable headline from a URL path slug."""
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        if domain.startswith("www."):
            domain = domain[4:]

        path = unquote(parsed.path).strip("/")
        if not path:
            return domain

        segments = [s for s in path.split("/") if s]
        slug = ""
        for seg in reversed(segments):
            for ext in (".html", ".htm", ".php", ".asp", ".aspx", ".shtml"):
                if seg.lower().endswith(ext):
                    seg = seg[: -len(ext)]
            if _is_gibberish(seg):
                continue
            slug = seg
            break

        if not slug:
            return domain

        slug = re.sub(r"^[\d]+-", "", slug)
        slug = re.sub(r"-[\da-f]{6,}$", "", slug)
        slug = re.sub(r"[-_]c-\d+$", "", slug)
        slug = re.sub(r"^p=\d+$", "", slug)
        slug = slug.replace("-", " ").replace("_", " ")
        slug = re.sub(r"\s+", " ", slug).strip()

        if len(slug) < 8 or _is_gibberish(slug.replace(" ", "-")):
            return domain

        headline = slug.title()
        if len(headline) > 90:
            headline = headline[:87] + "..."
        return headline
    except (ValueError, AttributeError):
        return url[:60]


# ---------------------------------------------------------------------------
# GDELT Events
# ---------------------------------------------------------------------------

# CAMEO root codes for conflict/military events
_CONFLICT_CODES = {"14", "17", "18", "19", "20"}


def _parse_gdelt_export_zip(
    zip_bytes: bytes,
    seen_locs: set[str],
    features: list[dict],
    loc_index: dict[str, int],
) -> None:
    """Parse a single GDELT export ZIP and append conflict features."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as cf:
            reader = csv.reader(
                io.TextIOWrapper(cf, encoding="utf-8", errors="replace"),
                delimiter="\t",
            )
            for row in reader:
                try:
                    if len(row) < 61:
                        continue
                    event_code = row[26][:2] if len(row[26]) >= 2 else ""
                    if event_code not in _CONFLICT_CODES:
                        continue
                    lat = float(row[56]) if row[56] else None
                    lng = float(row[57]) if row[57] else None
                    if lat is None or lng is None or (lat == 0 and lng == 0):
                        continue

                    source_url = row[60].strip() if len(row) > 60 else ""
                    location = row[52].strip() if len(row) > 52 else "Unknown"
                    actor1 = row[6].strip() if len(row) > 6 else ""
                    actor2 = row[16].strip() if len(row) > 16 else ""
                    tone = float(row[34]) if len(row) > 34 and row[34] else 0.0

                    loc_key = f"{round(lat, 1)}_{round(lng, 1)}"
                    if loc_key in seen_locs:
                        idx = loc_index[loc_key]
                        feat = features[idx]
                        feat["_count"] = feat.get("_count", 1) + 1
                        urls = feat.get("_urls", [])
                        seen_domains = feat.get("_domains", set())
                        if source_url:
                            domain = _extract_domain(source_url)
                            if domain not in seen_domains and len(urls) < 10:
                                urls.append(source_url)
                                seen_domains.add(domain)
                                feat["_urls"] = urls
                                feat["_domains"] = seen_domains
                        continue

                    seen_locs.add(loc_key)
                    title = (
                        location
                        or (f"{actor1} vs {actor2}" if actor1 and actor2 else actor1)
                        or "Unknown Incident"
                    )
                    domain = _extract_domain(source_url) if source_url else ""
                    loc_index[loc_key] = len(features)
                    features.append(
                        {
                            "lat": lat,
                            "lng": lng,
                            "title": title,
                            "url": source_url,
                            "tone": round(tone, 2),
                            "source": domain,
                            "date": "",
                            "_count": 1,
                            "_urls": [source_url] if source_url else [],
                            "_domains": {domain} if domain else set(),
                            "_loc_key": loc_key,
                        }
                    )
                except (ValueError, IndexError):
                    continue
    except (IOError, OSError, ValueError, zipfile.BadZipFile) as exc:
        logger.warning("gdelt.parse_zip_failed", error=str(exc))


async def _download_gdelt_zip(url: str) -> bytes | None:
    """Download a single GDELT export ZIP file."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except (aiohttp.ClientError, TimeoutError, OSError):
        pass
    return None


async def fetch_gdelt() -> list[dict]:
    """Fetch global conflict events from GDELT event export files.

    Aggregates the last ~8 hours of 15-minute exports.
    Returns a list of dicts, each with keys:
        lat, lng, title, url, tone, source, date
    """
    try:
        index_text = await fetch_text(
            "http://data.gdeltproject.org/gdeltv2/lastupdate.txt",
            timeout=10,
        )

        latest_url: str | None = None
        for line in index_text.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 3 and parts[2].endswith(".export.CSV.zip"):
                latest_url = parts[2]
                break

        if not latest_url:
            logger.error("gdelt.no_export_url")
            return []

        ts_match = re.search(r"(\d{14})\.export\.CSV\.zip", latest_url)
        if not ts_match:
            logger.error("gdelt.bad_timestamp")
            return []

        latest_ts = datetime.strptime(ts_match.group(1), "%Y%m%d%H%M%S")

        # Generate URLs for the last 8 hours (32 files at 15-min intervals)
        num_files = 32
        urls: list[str] = []
        for i in range(num_files):
            ts = latest_ts - timedelta(minutes=15 * i)
            fname = ts.strftime("%Y%m%d%H%M%S") + ".export.CSV.zip"
            urls.append(f"http://data.gdeltproject.org/gdeltv2/{fname}")

        logger.info("gdelt.downloading_exports", count=len(urls))

        # Download all ZIPs concurrently
        import asyncio

        zip_results = await asyncio.gather(*[_download_gdelt_zip(u) for u in urls])

        successful = sum(1 for r in zip_results if r is not None)
        logger.info("gdelt.downloads_complete", successful=successful, total=len(urls))

        # Parse all downloaded files
        features: list[dict] = []
        seen_locs: set[str] = set()
        loc_index: dict[str, int] = {}

        for zip_bytes in zip_results:
            if zip_bytes:
                _parse_gdelt_export_zip(zip_bytes, seen_locs, features, loc_index)

        # Build final output -- strip internal tracking fields
        results: list[dict] = []
        for f in features:
            headline = _url_to_headline(f["url"]) if f["url"] else f["title"]
            results.append(
                {
                    "lat": f["lat"],
                    "lng": f["lng"],
                    "title": headline,
                    "url": f["url"],
                    "tone": f["tone"],
                    "source": f["source"],
                    "date": f["date"],
                }
            )

        logger.info("gdelt.done", events=len(results), files_parsed=successful)
        return results

    except Exception as exc:
        logger.error("gdelt.fetch_failed", error=str(exc))
        return []


# ---------------------------------------------------------------------------
# DeepStateMap Frontlines
# ---------------------------------------------------------------------------

# Zone index -> label (based on DeepStateMap frontend mapping)
_ZONE_NAMES: dict[int, str] = {
    0: "Russian-occupied areas",
    1: "Russian advance",
    2: "Liberated area",
    3: "Russian-occupied areas",  # Crimea / LPR / DPR
    4: "Directions of UA attacks",
}


async def fetch_frontlines() -> dict | None:
    """Fetch the latest Ukraine frontline GeoJSON from the DeepStateMap GitHub mirror.

    Returns a GeoJSON FeatureCollection with zone labels, or None on failure.
    """
    try:
        logger.info("frontlines.fetching_deepstatemap")

        # Query the repo tree to find the latest GeoJSON file
        tree_url = "https://api.github.com/repos/cyterat/deepstate-map-data/git/trees/main?recursive=1"
        tree_data = await fetch_json(tree_url, timeout=10, retries=2)

        tree_items = tree_data.get("tree", [])
        geo_files = [
            item["path"]
            for item in tree_items
            if item["path"].startswith("data/deepstatemap_data_")
            and item["path"].endswith(".geojson")
        ]

        if not geo_files:
            logger.error("frontlines.no_geojson_files")
            return None

        latest_file = sorted(geo_files)[-1]
        raw_url = f"https://raw.githubusercontent.com/cyterat/deepstate-map-data/main/{latest_file}"
        logger.info("frontlines.downloading", file=latest_file)

        data = await fetch_json(raw_url, timeout=20, retries=2)

        if "features" not in data:
            logger.error("frontlines.invalid_geojson")
            return None

        # Annotate each feature with zone labels
        for idx, feature in enumerate(data["features"]):
            if "properties" not in feature or feature["properties"] is None:
                feature["properties"] = {}
            feature["properties"]["name"] = _ZONE_NAMES.get(idx, "Russian-occupied areas")
            feature["properties"]["zone_id"] = idx

        logger.info("frontlines.done", features=len(data["features"]))
        return data

    except Exception as exc:
        logger.error("frontlines.fetch_failed", error=str(exc))
        return None

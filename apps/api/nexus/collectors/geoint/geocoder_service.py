"""Nominatim geocoding service — forward/reverse geocoding via OSM Nominatim."""

from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"


class GeocoderService(BaseCollector):
    """Forward and reverse geocoding via Nominatim (OpenStreetMap)."""

    def __init__(self) -> None:
        super().__init__(rate_limit=1.0, max_retries=3)  # Nominatim: max 1 req/s

    async def _get_headers(self) -> dict[str, str]:
        """Headers required by Nominatim usage policy."""
        return {
            "User-Agent": settings.nominatim_user_agent,
            "Accept": "application/json",
        }

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Geocode. scan_types: geocode_forward, geocode_reverse, geocode_batch."""
        scan_type = query.scan_type
        results: list[CollectionResult] = []

        if scan_type == "geocode_forward":
            results = await self.forward_geocode(query.query)
        elif scan_type == "geocode_reverse":
            lat = query.options.get("latitude", 0.0)
            lon = query.options.get("longitude", 0.0)
            results = await self.reverse_geocode(lat, lon)
        elif scan_type == "geocode_batch":
            placenames = query.options.get("placenames", [query.query])
            results = await self.batch_geocode(placenames)
        else:
            results = await self.forward_geocode(query.query)

        logger.info(
            "geocoder.collected",
            scan_type=scan_type,
            result_count=len(results),
        )
        return results

    async def forward_geocode(self, placename: str) -> list[CollectionResult]:
        """Convert a placename to WGS84 coordinates."""
        await self._rate_limit_wait()

        url = f"{NOMINATIM_BASE}/search"
        params = {
            "q": placename,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
        }

        try:
            session = await self._get_session()
            headers = await self._get_headers()
            async with session.get(url, params=params, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as e:
            logger.error("geocoder.forward_error", placename=placename, error=str(e))
            return []

        results: list[CollectionResult] = []
        for place in data:
            address = place.get("address", {})
            normalized: dict[str, Any] = {
                "entity_type": "Location",
                "display_name": place.get("display_name", ""),
                "name": place.get("name", placename),
                "latitude": float(place.get("lat", 0)),
                "longitude": float(place.get("lon", 0)),
                "osm_type": place.get("osm_type", ""),
                "osm_id": str(place.get("osm_id", "")),
                "place_type": place.get("type", ""),
                "category": place.get("category", ""),
                "country": address.get("country", ""),
                "country_code": address.get("country_code", ""),
                "state": address.get("state", ""),
                "city": address.get("city", "") or address.get("town", "") or address.get("village", ""),
                "bounding_box": place.get("boundingbox", []),
                "importance": place.get("importance", 0.0),
            }

            results.append(
                CollectionResult(
                    source_int="GEOINT",
                    source_id=f"nominatim:{place.get('osm_type', '')}/{place.get('osm_id', '')}",
                    raw_data=place,
                    normalized=normalized,
                    metadata={
                        "collector": "nominatim",
                        "scan_type": "geocode_forward",
                        "query": placename,
                    },
                    reliability_grade="C",
                )
            )

        return results

    async def reverse_geocode(self, lat: float, lon: float) -> list[CollectionResult]:
        """Convert coordinates to place information."""
        await self._rate_limit_wait()

        url = f"{NOMINATIM_BASE}/reverse"
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
        }

        try:
            session = await self._get_session()
            headers = await self._get_headers()
            async with session.get(url, params=params, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as e:
            logger.error("geocoder.reverse_error", lat=lat, lon=lon, error=str(e))
            return []

        if "error" in data:
            return []

        address = data.get("address", {})
        normalized: dict[str, Any] = {
            "entity_type": "Location",
            "display_name": data.get("display_name", ""),
            "name": data.get("name", "") or address.get("city", "") or address.get("town", ""),
            "latitude": lat,
            "longitude": lon,
            "osm_type": data.get("osm_type", ""),
            "osm_id": str(data.get("osm_id", "")),
            "place_type": data.get("type", ""),
            "category": data.get("category", ""),
            "country": address.get("country", ""),
            "country_code": address.get("country_code", ""),
            "state": address.get("state", ""),
            "city": address.get("city", "") or address.get("town", "") or address.get("village", ""),
        }

        return [
            CollectionResult(
                source_int="GEOINT",
                source_id=f"nominatim:reverse:{lat:.6f},{lon:.6f}",
                raw_data=data,
                normalized=normalized,
                metadata={
                    "collector": "nominatim",
                    "scan_type": "geocode_reverse",
                },
                reliability_grade="C",
            )
        ]

    async def batch_geocode(self, placenames: list[str]) -> list[CollectionResult]:
        """Geocode multiple placenames sequentially (respecting rate limit)."""
        all_results: list[CollectionResult] = []
        for placename in placenames:
            results = await self.forward_geocode(placename)
            if results:
                all_results.append(results[0])  # Take top result per placename
        return all_results

    async def health_check(self) -> bool:
        """Check if Nominatim API is reachable."""
        try:
            session = await self._get_session()
            headers = await self._get_headers()
            async with session.get(
                f"{NOMINATIM_BASE}/status",
                headers=headers,
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

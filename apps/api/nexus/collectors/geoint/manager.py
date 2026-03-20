"""GEOINT collection manager — orchestrates all GEOINT collectors."""

import asyncio
from typing import Any

import structlog

from nexus.collectors.base import CollectionQuery, CollectionResult
from nexus.collectors.geoint.sentinel_collector import SentinelCollector
from nexus.collectors.geoint.overpass_collector import OverpassCollector
from nexus.collectors.geoint.geocoder_service import GeocoderService

logger = structlog.get_logger()


class GeointManager:
    """Orchestrates GEOINT data collection across all sub-collectors."""

    def __init__(self) -> None:
        self.sentinel = SentinelCollector()
        self.overpass = OverpassCollector()
        self.geocoder = GeocoderService()

    async def collect(
        self, query: str, scan_type: str, options: dict[str, Any] | None = None
    ) -> list[CollectionResult]:
        """Route scan_type to appropriate collector."""
        cq = CollectionQuery(query=query, scan_type=scan_type, options=options or {})
        results: list[CollectionResult] = []

        if scan_type == "full":
            # Run all collectors in parallel
            tasks = [
                self.sentinel.collect(
                    CollectionQuery(query=query, scan_type="satellite_search", options=options or {})
                ),
                self.overpass.collect(
                    CollectionQuery(query=query, scan_type="osm_bbox", options=options or {})
                ),
                self.geocoder.collect(
                    CollectionQuery(query=query, scan_type="geocode_forward", options=options or {})
                ),
            ]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for result in gathered:
                if isinstance(result, list):
                    results.extend(result)
                elif isinstance(result, Exception):
                    logger.error("geoint.collector_failed", error=str(result))

        elif scan_type.startswith("satellite_"):
            results.extend(await self.sentinel.collect(cq))

        elif scan_type.startswith("osm_"):
            results.extend(await self.overpass.collect(cq))

        elif scan_type.startswith("geocode_"):
            results.extend(await self.geocoder.collect(cq))

        else:
            # Default: run geocoder
            results.extend(
                await self.geocoder.collect(
                    CollectionQuery(query=query, scan_type="geocode_forward")
                )
            )

        logger.info(
            "geoint.collection_complete",
            query=query,
            scan_type=scan_type,
            total_results=len(results),
        )
        return results

    async def health_check(self) -> dict[str, bool]:
        """Check health of all GEOINT collectors."""
        checks = await asyncio.gather(
            self.sentinel.health_check(),
            self.overpass.health_check(),
            self.geocoder.health_check(),
            return_exceptions=True,
        )

        return {
            "sentinel": checks[0] if isinstance(checks[0], bool) else False,
            "overpass": checks[1] if isinstance(checks[1], bool) else False,
            "geocoder": checks[2] if isinstance(checks[2], bool) else False,
        }

    async def close(self) -> None:
        """Close all collector sessions."""
        await asyncio.gather(
            self.sentinel.close(),
            self.overpass.close(),
            self.geocoder.close(),
        )

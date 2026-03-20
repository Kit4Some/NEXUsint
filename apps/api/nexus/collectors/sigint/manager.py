"""SIGINT collection manager — orchestrates all SIGINT collectors."""

import asyncio
from typing import Any

import structlog

from nexus.collectors.base import CollectionQuery, CollectionResult
from nexus.collectors.sigint.adsb_collector import ADSBCollector
from nexus.collectors.sigint.ais_collector import AISCollector

logger = structlog.get_logger()


class SigntManager:
    """Orchestrates SIGINT data collection across all sub-collectors."""

    def __init__(self) -> None:
        self.adsb = ADSBCollector()
        self.ais = AISCollector()

    async def collect(
        self, query: str, scan_type: str, options: dict[str, Any] | None = None
    ) -> list[CollectionResult]:
        """Run appropriate collectors based on scan type."""
        cq = CollectionQuery(query=query, scan_type=scan_type, options=options or {})
        results: list[CollectionResult] = []

        if scan_type == "full":
            tasks = [
                self.adsb.collect(CollectionQuery(query=query, scan_type="aircraft_state")),
                self.ais.collect(CollectionQuery(query=query, scan_type="vessel_position")),
            ]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for result in gathered:
                if isinstance(result, list):
                    results.extend(result)
                elif isinstance(result, Exception):
                    logger.error("sigint.collector_failed", error=str(result))

        elif scan_type.startswith("aircraft_") or scan_type in ("arrivals", "departures"):
            results.extend(await self.adsb.collect(cq))

        elif scan_type.startswith("vessel_"):
            results.extend(await self.ais.collect(cq))

        elif scan_type.startswith("area_"):
            # Area queries go to both collectors
            if scan_type == "area_aircraft":
                results.extend(await self.adsb.collect(cq))
            elif scan_type == "area_vessels":
                results.extend(await self.ais.collect(cq))
            else:
                # area_all: query both
                tasks = [
                    self.adsb.collect(
                        CollectionQuery(
                            query=query, scan_type="area_aircraft", options=cq.options
                        )
                    ),
                    self.ais.collect(
                        CollectionQuery(
                            query=query, scan_type="area_vessels", options=cq.options
                        )
                    ),
                ]
                gathered = await asyncio.gather(*tasks, return_exceptions=True)
                for result in gathered:
                    if isinstance(result, list):
                        results.extend(result)
                    elif isinstance(result, Exception):
                        logger.error("sigint.collector_failed", error=str(result))

        else:
            logger.warning("sigint.unknown_scan_type", scan_type=scan_type)

        logger.info(
            "sigint.collection_complete",
            query=query,
            scan_type=scan_type,
            total_results=len(results),
        )
        return results

    async def health_check(self) -> dict[str, bool]:
        """Check health of all SIGINT collectors."""
        checks = await asyncio.gather(
            self.adsb.health_check(),
            self.ais.health_check(),
            return_exceptions=True,
        )

        return {
            "adsb": checks[0] if isinstance(checks[0], bool) else False,
            "ais": checks[1] if isinstance(checks[1], bool) else False,
        }

    async def close(self) -> None:
        """Close all collector sessions."""
        await asyncio.gather(
            self.adsb.close(),
            self.ais.close(),
        )

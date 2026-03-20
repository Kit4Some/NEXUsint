"""AIS vessel tracking collector."""

from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()


class AISCollector(BaseCollector):
    """Collects vessel tracking data via AIS API."""

    def __init__(self) -> None:
        super().__init__(rate_limit=1.0, max_retries=3)
        self._api_key = settings.ais_api_key
        self._api_url = settings.ais_api_url.rstrip("/")

    async def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        if not self._api_key:
            logger.warning("ais.no_api_key")
            return []

        scan_type = query.scan_type
        try:
            if scan_type == "vessel_position":
                return await self._get_vessel_position(query.query)
            elif scan_type == "vessel_track":
                return await self._get_vessel_track(query.query, query.options)
            elif scan_type == "area_vessels":
                return await self._get_area_vessels(query.options)
            elif scan_type == "vessel_info":
                return await self._get_vessel_info(query.query)
            else:
                logger.warning("ais.unknown_scan_type", scan_type=scan_type)
                return []
        except Exception as e:
            logger.error("ais.collection_failed", error=str(e), scan_type=scan_type)
            return []

    def _normalize_vessel(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize vessel data to standard format."""
        return {
            "entity_type": "Vessel",
            "mmsi": str(data.get("mmsi", data.get("MMSI", ""))),
            "imo": str(data.get("imo", data.get("IMO", ""))),
            "name": data.get("name", data.get("shipName", data.get("ship_name", ""))),
            "flag": data.get("flag", data.get("country", "")),
            "vessel_type": data.get("vessel_type", data.get("shipType", data.get("type", ""))),
            "latitude": data.get("latitude", data.get("lat", data.get("LAT"))),
            "longitude": data.get("longitude", data.get("lon", data.get("LON"))),
            "speed": data.get("speed", data.get("sog", data.get("SOG"))),
            "heading": data.get("heading", data.get("cog", data.get("COG"))),
            "destination": data.get("destination", ""),
            "draught": data.get("draught", data.get("draft")),
            "length": data.get("length", data.get("dimA", 0)) + data.get("dimB", 0)
            if isinstance(data.get("dimA"), (int, float))
            else data.get("length"),
            "status": data.get("status", data.get("navigational_status", "")),
        }

    async def _get_vessel_position(self, mmsi: str) -> list[CollectionResult]:
        """Get current position of a vessel by MMSI."""
        data = await self._request_with_retry(
            "GET",
            f"{self._api_url}/v1/vessels/{mmsi}/position",
            headers=await self._get_headers(),
        )

        normalized = self._normalize_vessel(data)
        return [CollectionResult(
            source_int="SIGINT",
            source_id=f"ais:position:{mmsi}",
            raw_data=data,
            normalized=normalized,
            metadata={"collector": "ais", "scan_type": "vessel_position"},
            reliability_grade="B",
        )]

    async def _get_vessel_track(
        self, mmsi: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get historical track of a vessel."""
        params: dict[str, Any] = {}
        if "start_time" in options:
            params["from"] = options["start_time"]
        if "end_time" in options:
            params["to"] = options["end_time"]

        data = await self._request_with_retry(
            "GET",
            f"{self._api_url}/v1/vessels/{mmsi}/track",
            params=params,
            headers=await self._get_headers(),
        )

        positions = data if isinstance(data, list) else data.get("positions", data.get("track", []))
        waypoints = []
        for pos in positions:
            waypoints.append({
                "timestamp": pos.get("timestamp", pos.get("time")),
                "latitude": pos.get("latitude", pos.get("lat")),
                "longitude": pos.get("longitude", pos.get("lon")),
                "speed": pos.get("speed", pos.get("sog")),
                "heading": pos.get("heading", pos.get("cog")),
            })

        if not waypoints:
            return []

        return [CollectionResult(
            source_int="SIGINT",
            source_id=f"ais:track:{mmsi}",
            raw_data=data if isinstance(data, dict) else {"positions": data},
            normalized={
                "entity_type": "VoyageTrack",
                "mmsi": mmsi,
                "waypoints": waypoints,
            },
            metadata={"collector": "ais", "scan_type": "vessel_track"},
            reliability_grade="B",
        )]

    async def _get_area_vessels(self, options: dict[str, Any]) -> list[CollectionResult]:
        """Get all vessels in a bounding box."""
        params = {
            "south": options.get("south", 0),
            "west": options.get("west", 0),
            "north": options.get("north", 0),
            "east": options.get("east", 0),
        }

        data = await self._request_with_retry(
            "GET",
            f"{self._api_url}/v1/vessels/area",
            params=params,
            headers=await self._get_headers(),
        )

        vessels = data if isinstance(data, list) else data.get("vessels", data.get("data", []))
        results: list[CollectionResult] = []
        for vessel in vessels:
            normalized = self._normalize_vessel(vessel)
            if normalized["latitude"] is not None and normalized["longitude"] is not None:
                results.append(CollectionResult(
                    source_int="SIGINT",
                    source_id=f"ais:position:{normalized['mmsi']}",
                    raw_data=vessel,
                    normalized=normalized,
                    metadata={"collector": "ais", "scan_type": "area_vessels"},
                    reliability_grade="B",
                ))

        logger.info("ais.area_vessels", count=len(results))
        return results

    async def _get_vessel_info(self, mmsi: str) -> list[CollectionResult]:
        """Get detailed vessel information."""
        data = await self._request_with_retry(
            "GET",
            f"{self._api_url}/v1/vessels/{mmsi}",
            headers=await self._get_headers(),
        )

        normalized = self._normalize_vessel(data)
        return [CollectionResult(
            source_int="SIGINT",
            source_id=f"ais:info:{mmsi}",
            raw_data=data,
            normalized=normalized,
            metadata={"collector": "ais", "scan_type": "vessel_info"},
            reliability_grade="B",
        )]

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            await self._request_with_retry(
                "GET",
                f"{self._api_url}/v1/health",
                headers=await self._get_headers(),
            )
            return True
        except Exception:
            return False

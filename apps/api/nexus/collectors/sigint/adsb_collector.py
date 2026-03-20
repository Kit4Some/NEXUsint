"""ADS-B aircraft tracking collector using OpenSky Network API."""

from typing import Any

import aiohttp
import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()

OPENSKY_API_BASE = "https://opensky-network.org/api"

# OpenSky state vector field indices
_ICAO24 = 0
_CALLSIGN = 1
_ORIGIN_COUNTRY = 2
_TIME_POSITION = 3
_LAST_CONTACT = 4
_LONGITUDE = 5
_LATITUDE = 6
_BARO_ALTITUDE = 7
_ON_GROUND = 8
_VELOCITY = 9
_TRUE_TRACK = 10
_VERTICAL_RATE = 11
_SENSORS = 12
_GEO_ALTITUDE = 13
_SQUAWK = 14
_SPI = 15
_POSITION_SOURCE = 16


class ADSBCollector(BaseCollector):
    """Collects aircraft data from OpenSky Network ADS-B API."""

    def __init__(self) -> None:
        # OpenSky: anonymous 1 req/10s, authenticated 1 req/5s
        has_auth = bool(settings.opensky_username and settings.opensky_password)
        rate = 0.2 if has_auth else 0.1
        super().__init__(rate_limit=rate, max_retries=3)
        self._username = settings.opensky_username
        self._password = settings.opensky_password

    def _auth(self) -> aiohttp.BasicAuth | None:
        if self._username and self._password:
            return aiohttp.BasicAuth(self._username, self._password)
        return None

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        scan_type = query.scan_type
        try:
            if scan_type == "aircraft_state":
                return await self._get_aircraft_state(query.query)
            elif scan_type == "area_aircraft":
                return await self._get_area_aircraft(query.options)
            elif scan_type == "aircraft_track":
                return await self._get_aircraft_track(query.query, query.options)
            elif scan_type in ("arrivals", "departures"):
                return await self._get_airport_flights(
                    query.query, scan_type, query.options
                )
            else:
                logger.warning("adsb.unknown_scan_type", scan_type=scan_type)
                return []
        except Exception as e:
            logger.error("adsb.collection_failed", error=str(e), scan_type=scan_type)
            return []

    def _normalize_state_vector(self, sv: list) -> dict[str, Any]:
        """Normalize an OpenSky state vector array to a dict."""
        return {
            "entity_type": "Aircraft",
            "icao24": sv[_ICAO24] or "",
            "callsign": (sv[_CALLSIGN] or "").strip(),
            "origin_country": sv[_ORIGIN_COUNTRY] or "",
            "latitude": sv[_LATITUDE],
            "longitude": sv[_LONGITUDE],
            "baro_altitude": sv[_BARO_ALTITUDE],
            "geo_altitude": sv[_GEO_ALTITUDE],
            "on_ground": sv[_ON_GROUND],
            "velocity": sv[_VELOCITY],
            "heading": sv[_TRUE_TRACK],
            "vertical_rate": sv[_VERTICAL_RATE],
            "squawk": sv[_SQUAWK] or "",
            "time_position": sv[_TIME_POSITION],
            "last_contact": sv[_LAST_CONTACT],
        }

    async def _get_aircraft_state(self, icao24: str) -> list[CollectionResult]:
        """Get current state of a specific aircraft by ICAO24."""
        data = await self._request_with_retry(
            "GET",
            f"{OPENSKY_API_BASE}/states/all",
            params={"icao24": icao24.lower()},
            auth=self._auth(),
        )

        results: list[CollectionResult] = []
        for sv in data.get("states", []):
            normalized = self._normalize_state_vector(sv)
            results.append(CollectionResult(
                source_int="SIGINT",
                source_id=f"opensky:state:{normalized['icao24']}",
                raw_data={"state_vector": sv, "time": data.get("time")},
                normalized=normalized,
                metadata={"collector": "adsb", "scan_type": "aircraft_state"},
                reliability_grade="B",
            ))

        logger.info("adsb.aircraft_state", icao24=icao24, found=len(results))
        return results

    async def _get_area_aircraft(self, options: dict[str, Any]) -> list[CollectionResult]:
        """Get all aircraft in a bounding box."""
        params: dict[str, Any] = {
            "lamin": options.get("south", 0),
            "lomin": options.get("west", 0),
            "lamax": options.get("north", 0),
            "lomax": options.get("east", 0),
        }

        data = await self._request_with_retry(
            "GET",
            f"{OPENSKY_API_BASE}/states/all",
            params=params,
            auth=self._auth(),
        )

        results: list[CollectionResult] = []
        for sv in data.get("states", []) or []:
            normalized = self._normalize_state_vector(sv)
            if normalized["latitude"] is not None and normalized["longitude"] is not None:
                results.append(CollectionResult(
                    source_int="SIGINT",
                    source_id=f"opensky:state:{normalized['icao24']}",
                    raw_data={"state_vector": sv, "time": data.get("time")},
                    normalized=normalized,
                    metadata={"collector": "adsb", "scan_type": "area_aircraft"},
                    reliability_grade="B",
                ))

        logger.info("adsb.area_aircraft", count=len(results))
        return results

    async def _get_aircraft_track(
        self, icao24: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get flight track waypoints for an aircraft."""
        params: dict[str, Any] = {"icao24": icao24.lower(), "time": 0}
        if "time" in options:
            params["time"] = options["time"]

        data = await self._request_with_retry(
            "GET",
            f"{OPENSKY_API_BASE}/tracks/all",
            params=params,
            auth=self._auth(),
        )

        waypoints = []
        for wp in data.get("path", []):
            waypoints.append({
                "timestamp": wp[0],
                "latitude": wp[1],
                "longitude": wp[2],
                "baro_altitude": wp[3],
                "heading": wp[4],
                "on_ground": wp[5],
            })

        if not waypoints:
            return []

        return [CollectionResult(
            source_int="SIGINT",
            source_id=f"opensky:track:{icao24.lower()}",
            raw_data=data,
            normalized={
                "entity_type": "FlightPath",
                "icao24": data.get("icao24", icao24),
                "callsign": (data.get("callsign") or "").strip(),
                "start_time": data.get("startTime"),
                "end_time": data.get("endTime"),
                "waypoints": waypoints,
            },
            metadata={"collector": "adsb", "scan_type": "aircraft_track"},
            reliability_grade="B",
        )]

    async def _get_airport_flights(
        self, airport_icao: str, direction: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get arrivals or departures for an airport."""
        import time as _time

        end = options.get("end", int(_time.time()))
        begin = options.get("begin", end - 7200)  # Default: last 2 hours

        endpoint = "arrivals" if direction == "arrivals" else "departures"
        data = await self._request_with_retry(
            "GET",
            f"{OPENSKY_API_BASE}/flights/{endpoint}",
            params={"airport": airport_icao.upper(), "begin": begin, "end": end},
            auth=self._auth(),
        )

        results: list[CollectionResult] = []
        for flight in data if isinstance(data, list) else []:
            results.append(CollectionResult(
                source_int="SIGINT",
                source_id=f"opensky:{direction}:{flight.get('icao24', '')}:{flight.get('firstSeen', '')}",
                raw_data=flight,
                normalized={
                    "entity_type": "Aircraft",
                    "icao24": flight.get("icao24", ""),
                    "callsign": (flight.get("callsign") or "").strip(),
                    "departure_airport": flight.get("estDepartureAirport", ""),
                    "arrival_airport": flight.get("estArrivalAirport", ""),
                    "first_seen": flight.get("firstSeen"),
                    "last_seen": flight.get("lastSeen"),
                },
                metadata={
                    "collector": "adsb",
                    "scan_type": direction,
                    "airport": airport_icao,
                },
                reliability_grade="B",
            ))

        logger.info(
            f"adsb.{direction}",
            airport=airport_icao,
            count=len(results),
        )
        return results

    async def health_check(self) -> bool:
        try:
            await self._request_with_retry(
                "GET",
                f"{OPENSKY_API_BASE}/states/all",
                params={"lamin": 45, "lomin": -1, "lamax": 46, "lomax": 0},
                auth=self._auth(),
            )
            return True
        except Exception:
            return False

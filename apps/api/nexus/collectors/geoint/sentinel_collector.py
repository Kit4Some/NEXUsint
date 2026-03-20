"""Copernicus Sentinel-2 satellite imagery collector via ODATA API."""

from datetime import datetime
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()

IDENTITY_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
ODATA_CATALOG_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"


class SentinelCollector(BaseCollector):
    """Collects Sentinel-2 satellite imagery metadata via Copernicus Data Space ODATA API."""

    def __init__(self) -> None:
        super().__init__(rate_limit=0.5, max_retries=3)
        self._token: str | None = None
        self._token_expires: float = 0.0

    async def _authenticate(self) -> str:
        """Get OAuth2 access token from Copernicus Identity Service."""
        import asyncio

        now = asyncio.get_event_loop().time()
        if self._token and now < self._token_expires:
            return self._token

        session = await self._get_session()
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.copernicus_client_id,
            "client_secret": settings.copernicus_client_secret,
        }

        async with session.post(IDENTITY_URL, data=data) as resp:
            resp.raise_for_status()
            body = await resp.json()
            self._token = body["access_token"]
            self._token_expires = now + body.get("expires_in", 300) - 30
            return self._token

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Query Sentinel-2 catalog. scan_types: satellite_search, satellite_metadata."""
        scan_type = query.scan_type
        results: list[CollectionResult] = []

        if scan_type == "satellite_search":
            bbox = query.options.get("bbox", {})
            results = await self._search_products(
                bbox=(
                    bbox.get("west", -180),
                    bbox.get("south", -90),
                    bbox.get("east", 180),
                    bbox.get("north", 90),
                ),
                date_start=query.options.get("date_start", ""),
                date_end=query.options.get("date_end", ""),
                max_cloud_cover=query.options.get("max_cloud_cover", 20.0),
            )
        elif scan_type == "satellite_metadata":
            product_id = query.query
            results = await self._get_product_metadata(product_id)
        else:
            results = await self._search_products(
                bbox=(-180, -90, 180, 90),
                date_start="",
                date_end="",
            )

        logger.info(
            "sentinel.collected",
            scan_type=scan_type,
            result_count=len(results),
        )
        return results

    async def _search_products(
        self,
        bbox: tuple[float, float, float, float],
        date_start: str,
        date_end: str,
        max_cloud_cover: float = 20.0,
    ) -> list[CollectionResult]:
        """Search ODATA catalog for Sentinel-2 L2A products in bounding box."""
        await self._rate_limit_wait()

        west, south, east, north = bbox
        polygon = (
            f"POLYGON(({west} {south},{east} {south},"
            f"{east} {north},{west} {north},{west} {south}))"
        )

        filters = [
            "Collection/Name eq 'SENTINEL-2'",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{polygon}')",
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {max_cloud_cover})",
        ]

        if date_start:
            filters.append(f"ContentDate/Start ge {date_start}T00:00:00.000Z")
        if date_end:
            filters.append(f"ContentDate/Start le {date_end}T23:59:59.999Z")

        filter_str = " and ".join(filters)
        params = {
            "$filter": filter_str,
            "$orderby": "ContentDate/Start desc",
            "$top": 20,
            "$expand": "Attributes",
        }

        try:
            session = await self._get_session()
            async with session.get(ODATA_CATALOG_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as e:
            logger.error("sentinel.search_error", error=str(e))
            return []

        results: list[CollectionResult] = []
        for product in data.get("value", []):
            attrs = {}
            for attr in product.get("Attributes", []):
                attrs[attr.get("Name", "")] = attr.get("Value")

            cloud_cover = attrs.get("cloudCover", None)
            footprint = product.get("GeoFootprint", {}).get("coordinates", [])

            # Compute centroid from footprint for entity position
            lat, lon = 0.0, 0.0
            if footprint:
                coords = footprint[0] if isinstance(footprint[0], list) and footprint[0] and isinstance(footprint[0][0], list) else footprint
                if coords and isinstance(coords[0], list):
                    flat = coords[0] if isinstance(coords[0][0], (int, float)) else coords[0]
                    lons = [c[0] for c in flat]
                    lats = [c[1] for c in flat]
                    lon = sum(lons) / len(lons)
                    lat = sum(lats) / len(lats)

            normalized: dict[str, Any] = {
                "entity_type": "SatelliteImage",
                "product_id": product.get("Id", ""),
                "name": product.get("Name", ""),
                "acquisition_date": product.get("ContentDate", {}).get("Start", ""),
                "cloud_cover": cloud_cover,
                "bbox": {"west": west, "south": south, "east": east, "north": north},
                "footprint": footprint,
                "latitude": lat,
                "longitude": lon,
                "resolution": attrs.get("resolution", "10m"),
                "processing_level": attrs.get("processingLevel", "Level-2A"),
                "size_mb": product.get("ContentLength", 0) / (1024 * 1024),
            }

            results.append(
                CollectionResult(
                    source_int="GEOINT",
                    source_id=f"sentinel:{product.get('Id', '')}",
                    raw_data=product,
                    normalized=normalized,
                    metadata={
                        "collector": "sentinel",
                        "scan_type": "satellite_search",
                        "platform": "Sentinel-2",
                    },
                    reliability_grade="B",
                )
            )

        return results

    async def _get_product_metadata(self, product_id: str) -> list[CollectionResult]:
        """Get detailed metadata for a specific Sentinel-2 product."""
        await self._rate_limit_wait()

        url = f"{ODATA_CATALOG_URL}('{product_id}')"
        params = {"$expand": "Attributes"}

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as resp:
                resp.raise_for_status()
                product = await resp.json()
        except Exception as e:
            logger.error("sentinel.metadata_error", product_id=product_id, error=str(e))
            return []

        attrs = {}
        for attr in product.get("Attributes", []):
            attrs[attr.get("Name", "")] = attr.get("Value")

        normalized: dict[str, Any] = {
            "entity_type": "SatelliteImage",
            "product_id": product_id,
            "name": product.get("Name", ""),
            "acquisition_date": product.get("ContentDate", {}).get("Start", ""),
            "cloud_cover": attrs.get("cloudCover"),
            "resolution": attrs.get("resolution", "10m"),
            "processing_level": attrs.get("processingLevel", "Level-2A"),
            "instrument": attrs.get("instrumentShortName", "MSI"),
            "orbit_number": attrs.get("orbitNumber"),
            "size_mb": product.get("ContentLength", 0) / (1024 * 1024),
        }

        return [
            CollectionResult(
                source_int="GEOINT",
                source_id=f"sentinel:{product_id}",
                raw_data=product,
                normalized=normalized,
                metadata={
                    "collector": "sentinel",
                    "scan_type": "satellite_metadata",
                    "platform": "Sentinel-2",
                },
                reliability_grade="B",
            )
        ]

    async def health_check(self) -> bool:
        """Check if Copernicus ODATA API is reachable."""
        try:
            session = await self._get_session()
            async with session.get(
                ODATA_CATALOG_URL, params={"$top": 1}
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

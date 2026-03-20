"""OpenStreetMap Overpass API collector for geographic features."""

from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult

logger = structlog.get_logger()

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"


class OverpassCollector(BaseCollector):
    """Collects geographic features from the OpenStreetMap Overpass API."""

    def __init__(self) -> None:
        super().__init__(rate_limit=0.2, max_retries=3)  # Overpass is rate-sensitive

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Query Overpass. scan_types: osm_bbox, osm_tag_search, osm_around."""
        scan_type = query.scan_type
        results: list[CollectionResult] = []

        if scan_type == "osm_bbox":
            bbox = query.options.get("bbox", {})
            tags = query.options.get("tags", {})
            results = await self._query_bbox(
                bbox=(
                    bbox.get("south", -90),
                    bbox.get("west", -180),
                    bbox.get("north", 90),
                    bbox.get("east", 180),
                ),
                tags=tags,
            )
        elif scan_type == "osm_tag_search":
            tags = query.options.get("tags", {})
            bbox = query.options.get("bbox", {})
            results = await self._query_bbox(
                bbox=(
                    bbox.get("south", -90),
                    bbox.get("west", -180),
                    bbox.get("north", 90),
                    bbox.get("east", 180),
                ),
                tags=tags,
            )
        elif scan_type == "osm_around":
            lat = query.options.get("latitude", 0.0)
            lon = query.options.get("longitude", 0.0)
            radius = query.options.get("radius", 1000)
            tags = query.options.get("tags", {})
            results = await self._query_around(lat, lon, radius, tags)
        else:
            # Default: treat query as a tag search
            results = await self._query_bbox(
                bbox=(-90, -180, 90, 180),
                tags={"name": query.query} if query.query else None,
            )

        logger.info(
            "overpass.collected",
            scan_type=scan_type,
            result_count=len(results),
        )
        return results

    async def _query_bbox(
        self,
        bbox: tuple[float, float, float, float],
        tags: dict[str, str] | None = None,
    ) -> list[CollectionResult]:
        """Query OSM features within a bounding box with optional tag filters."""
        south, west, north, east = bbox
        overpass_ql = self._build_overpass_query(bbox, tags)

        try:
            data = await self._execute_query(overpass_ql)
        except Exception as e:
            logger.error("overpass.bbox_error", error=str(e))
            return []

        return self._parse_elements(data.get("elements", []), "osm_bbox")

    async def _query_around(
        self,
        lat: float,
        lon: float,
        radius: float,
        tags: dict[str, str] | None = None,
    ) -> list[CollectionResult]:
        """Query OSM features around a point with a radius."""
        tag_filter = ""
        if tags:
            for key, value in tags.items():
                if value:
                    tag_filter += f'["{key}"="{value}"]'
                else:
                    tag_filter += f'["{key}"]'

        overpass_ql = f"""
[out:json][timeout:25];
(
  node{tag_filter}(around:{radius},{lat},{lon});
  way{tag_filter}(around:{radius},{lat},{lon});
);
out center body;
"""

        try:
            data = await self._execute_query(overpass_ql)
        except Exception as e:
            logger.error("overpass.around_error", error=str(e))
            return []

        return self._parse_elements(data.get("elements", []), "osm_around")

    def _build_overpass_query(
        self,
        bbox: tuple[float, float, float, float],
        tags: dict[str, str] | None,
    ) -> str:
        """Build Overpass QL query string."""
        south, west, north, east = bbox
        bbox_str = f"{south},{west},{north},{east}"

        tag_filter = ""
        if tags:
            for key, value in tags.items():
                if value:
                    tag_filter += f'["{key}"="{value}"]'
                else:
                    tag_filter += f'["{key}"]'

        return f"""
[out:json][timeout:25];
(
  node{tag_filter}({bbox_str});
  way{tag_filter}({bbox_str});
  relation{tag_filter}({bbox_str});
);
out center body;
"""

    async def _execute_query(self, overpass_ql: str) -> dict[str, Any]:
        """Execute an Overpass QL query."""
        await self._rate_limit_wait()
        session = await self._get_session()

        async with session.post(
            OVERPASS_API_URL,
            data={"data": overpass_ql},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _parse_elements(
        self,
        elements: list[dict[str, Any]],
        scan_type: str,
    ) -> list[CollectionResult]:
        """Parse Overpass response elements into CollectionResults."""
        results: list[CollectionResult] = []

        for elem in elements:
            osm_type = elem.get("type", "node")
            osm_id = elem.get("id", "")
            tags = elem.get("tags", {})

            # Get coordinates — nodes have lat/lon directly, ways/relations use center
            lat = elem.get("lat") or elem.get("center", {}).get("lat")
            lon = elem.get("lon") or elem.get("center", {}).get("lon")

            if lat is None or lon is None:
                continue

            name = (
                tags.get("name", "")
                or tags.get("name:en", "")
                or tags.get("ref", "")
                or f"{osm_type}/{osm_id}"
            )

            # Determine feature category from tags
            feature_type = "unknown"
            for key in ("amenity", "building", "landuse", "shop", "tourism",
                        "natural", "highway", "railway", "waterway", "leisure"):
                if key in tags:
                    feature_type = f"{key}:{tags[key]}"
                    break

            normalized: dict[str, Any] = {
                "entity_type": "GeoFeature",
                "osm_id": str(osm_id),
                "osm_type": osm_type,
                "name": name,
                "feature_type": feature_type,
                "latitude": lat,
                "longitude": lon,
                "tags": tags,
            }

            results.append(
                CollectionResult(
                    source_int="GEOINT",
                    source_id=f"osm:{osm_type}/{osm_id}",
                    raw_data=elem,
                    normalized=normalized,
                    metadata={
                        "collector": "overpass",
                        "scan_type": scan_type,
                        "osm_type": osm_type,
                    },
                    reliability_grade="B",
                )
            )

        return results

    async def health_check(self) -> bool:
        """Check if Overpass API is reachable."""
        try:
            session = await self._get_session()
            test_query = "[out:json][timeout:5];node(1);out;"
            async with session.post(
                OVERPASS_API_URL,
                data={"data": test_query},
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

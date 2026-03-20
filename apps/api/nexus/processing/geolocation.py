"""Geolocation extraction from text, coordinates, IPs, and images."""

import math
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class GeoResult:
    """A single geolocation extraction result."""

    latitude: float
    longitude: float
    method: str  # "text", "coordinate", "ip", "exif"
    confidence: float
    source_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "method": self.method,
            "confidence": self.confidence,
            "source_text": self.source_text,
            "metadata": self.metadata,
        }


# Regex patterns for coordinate formats
_DD_PATTERN = re.compile(
    r"(-?\d{1,3}\.\d{2,8})\s*[,\s]\s*(-?\d{1,3}\.\d{2,8})"
)

_DMS_PATTERN = re.compile(
    r"""(\d{1,3})\s*[°]\s*(\d{1,2})\s*[′']\s*(\d{1,2}(?:\.\d+)?)\s*[″"]\s*([NSns])\s*[,\s]*"""
    r"""(\d{1,3})\s*[°]\s*(\d{1,2})\s*[′']\s*(\d{1,2}(?:\.\d+)?)\s*[″"]\s*([EWew])""",
    re.VERBOSE,
)

_UTM_PATTERN = re.compile(
    r"(\d{1,2})\s*([C-HJ-NP-X])\s+(\d{6,7})\s+(\d{6,7})"
)

_MGRS_PATTERN = re.compile(
    r"(\d{1,2})([C-HJ-NP-X])([A-HJ-NP-Z])([A-HJ-NP-V])\s*(\d{2,10})"
)


class GeoExtractor:
    """Multi-method geolocation extraction pipeline."""

    def __init__(
        self,
        geocoder_service: Any = None,
        geoip_db_path: str | None = None,
    ) -> None:
        self._geocoder = geocoder_service
        self._geoip_reader: Any = None
        if geoip_db_path:
            try:
                import geoip2.database

                self._geoip_reader = geoip2.database.Reader(geoip_db_path)
            except Exception as e:
                logger.warning("geoextractor.geoip_init_failed", error=str(e))

    async def extract_all(
        self,
        text: str,
        ips: list[str] | None = None,
        image_paths: list[str] | None = None,
    ) -> list[GeoResult]:
        """Run all extraction methods and return merged, deduplicated results."""
        results: list[GeoResult] = []

        # 1. Parse coordinates from text
        results.extend(self.parse_coordinates(text))

        # 2. Text-based geolocation (placenames → Nominatim)
        if self._geocoder:
            text_results = await self.extract_from_text(text)
            results.extend(text_results)

        # 3. IP-based geolocation
        if ips and self._geoip_reader:
            for ip in ips:
                geo = self.extract_from_ip(ip)
                if geo:
                    results.append(geo)

        # 4. Image-based (EXIF)
        if image_paths:
            for path in image_paths:
                geo = self.extract_from_exif(path)
                if geo:
                    results.append(geo)

        # Deduplicate results within ~100m of each other
        results = self._deduplicate(results, threshold_km=0.1)
        return results

    # --- Text-based geolocation ---

    async def extract_from_text(self, text: str) -> list[GeoResult]:
        """Extract placenames via NER, then geocode via Nominatim."""
        if not self._geocoder:
            return []

        # Extract location-like tokens using simple heuristics
        # (In production, this would use spaCy NER from the NERPipeline)
        import re as _re

        # Match capitalized multi-word phrases that might be placenames
        placename_pattern = _re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
        candidates = placename_pattern.findall(text)

        # Deduplicate
        seen: set[str] = set()
        unique_candidates: list[str] = []
        for name in candidates:
            lower = name.lower()
            if lower not in seen and len(name) > 2:
                seen.add(lower)
                unique_candidates.append(name)

        results: list[GeoResult] = []
        # Limit to top 5 to avoid excessive API calls
        for name in unique_candidates[:5]:
            try:
                from nexus.collectors.base import CollectionQuery

                geo_results = await self._geocoder.forward_geocode(name)
                if geo_results:
                    top = geo_results[0]
                    norm = top.normalized
                    results.append(
                        GeoResult(
                            latitude=norm.get("latitude", 0.0),
                            longitude=norm.get("longitude", 0.0),
                            method="text",
                            confidence=0.6 * norm.get("importance", 0.5),
                            source_text=name,
                            metadata={
                                "display_name": norm.get("display_name", ""),
                                "country": norm.get("country", ""),
                            },
                        )
                    )
            except Exception as e:
                logger.debug("geoextractor.text_geocode_failed", name=name, error=str(e))

        return results

    # --- Coordinate parsing ---

    def parse_coordinates(self, text: str) -> list[GeoResult]:
        """Parse DMS, DD, UTM, MGRS coordinate formats from text."""
        results: list[GeoResult] = []
        results.extend(self._parse_dms(text))
        results.extend(self._parse_dd(text))
        results.extend(self._parse_utm(text))
        results.extend(self._parse_mgrs(text))
        return results

    def _parse_dms(self, text: str) -> list[GeoResult]:
        """Parse Degrees-Minutes-Seconds: 40°26'46"N 79°58'56"W"""
        results: list[GeoResult] = []
        for match in _DMS_PATTERN.finditer(text):
            lat_d, lat_m, lat_s, lat_dir = (
                int(match.group(1)),
                int(match.group(2)),
                float(match.group(3)),
                match.group(4).upper(),
            )
            lon_d, lon_m, lon_s, lon_dir = (
                int(match.group(5)),
                int(match.group(6)),
                float(match.group(7)),
                match.group(8).upper(),
            )

            lat = lat_d + lat_m / 60 + lat_s / 3600
            lon = lon_d + lon_m / 60 + lon_s / 3600

            if lat_dir == "S":
                lat = -lat
            if lon_dir == "W":
                lon = -lon

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                results.append(
                    GeoResult(
                        latitude=lat,
                        longitude=lon,
                        method="coordinate",
                        confidence=0.95,
                        source_text=match.group(0),
                        metadata={"format": "DMS"},
                    )
                )

        return results

    def _parse_dd(self, text: str) -> list[GeoResult]:
        """Parse Decimal Degrees: 40.446195, -79.948862"""
        results: list[GeoResult] = []
        for match in _DD_PATTERN.finditer(text):
            lat = float(match.group(1))
            lon = float(match.group(2))

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                results.append(
                    GeoResult(
                        latitude=lat,
                        longitude=lon,
                        method="coordinate",
                        confidence=0.95,
                        source_text=match.group(0),
                        metadata={"format": "DD"},
                    )
                )

        return results

    def _parse_utm(self, text: str) -> list[GeoResult]:
        """Parse UTM: 17T 589160 4477528"""
        results: list[GeoResult] = []
        for match in _UTM_PATTERN.finditer(text):
            zone_number = int(match.group(1))
            zone_letter = match.group(2)
            easting = float(match.group(3))
            northing = float(match.group(4))

            try:
                from pyproj import Transformer

                is_northern = zone_letter >= "N"
                proj_str = f"+proj=utm +zone={zone_number} +{'north' if is_northern else 'south'} +datum=WGS84"
                transformer = Transformer.from_crs(proj_str, "EPSG:4326", always_xy=True)
                lon, lat = transformer.transform(easting, northing)

                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    results.append(
                        GeoResult(
                            latitude=lat,
                            longitude=lon,
                            method="coordinate",
                            confidence=0.90,
                            source_text=match.group(0),
                            metadata={
                                "format": "UTM",
                                "zone": f"{zone_number}{zone_letter}",
                            },
                        )
                    )
            except ImportError:
                logger.warning("geoextractor.pyproj_not_available")
            except Exception as e:
                logger.debug("geoextractor.utm_parse_failed", error=str(e))

        return results

    def _parse_mgrs(self, text: str) -> list[GeoResult]:
        """Parse MGRS: 17TLJ8916077528"""
        results: list[GeoResult] = []
        for match in _MGRS_PATTERN.finditer(text):
            mgrs_string = match.group(0).replace(" ", "")

            try:
                import mgrs as mgrs_lib

                m = mgrs_lib.MGRS()
                lat, lon = m.toLatLon(mgrs_string)

                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    results.append(
                        GeoResult(
                            latitude=lat,
                            longitude=lon,
                            method="coordinate",
                            confidence=0.90,
                            source_text=match.group(0),
                            metadata={"format": "MGRS"},
                        )
                    )
            except ImportError:
                logger.warning("geoextractor.mgrs_not_available")
            except Exception as e:
                logger.debug("geoextractor.mgrs_parse_failed", error=str(e))

        return results

    # --- IP-based geolocation ---

    def extract_from_ip(self, ip_address: str) -> GeoResult | None:
        """Lookup IP in MaxMind GeoIP2 database."""
        if not self._geoip_reader:
            return None

        try:
            response = self._geoip_reader.city(ip_address)
            location = response.location

            if location.latitude is None or location.longitude is None:
                return None

            return GeoResult(
                latitude=location.latitude,
                longitude=location.longitude,
                method="ip",
                confidence=0.5,  # IP geolocation has moderate accuracy
                source_text=ip_address,
                metadata={
                    "country": response.country.name or "",
                    "country_code": response.country.iso_code or "",
                    "city": response.city.name or "",
                    "accuracy_radius_km": location.accuracy_radius or 0,
                },
            )
        except Exception as e:
            logger.debug("geoextractor.ip_lookup_failed", ip=ip_address, error=str(e))
            return None

    # --- Image-based geolocation ---

    def extract_from_exif(self, image_path: str) -> GeoResult | None:
        """Extract GPS coordinates from image EXIF metadata."""
        try:
            from PIL import Image
            from PIL.ExifTags import GPSTAGS, TAGS

            img = Image.open(image_path)
            exif_data = img._getexif()

            if not exif_data:
                return None

            gps_info: dict[str, Any] = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == "GPSInfo":
                    for gps_tag_id, gps_value in value.items():
                        gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_info[gps_tag_name] = gps_value

            if "GPSLatitude" not in gps_info or "GPSLongitude" not in gps_info:
                return None

            lat = self._gps_to_decimal(
                gps_info["GPSLatitude"],
                gps_info.get("GPSLatitudeRef", "N"),
            )
            lon = self._gps_to_decimal(
                gps_info["GPSLongitude"],
                gps_info.get("GPSLongitudeRef", "E"),
            )

            return GeoResult(
                latitude=lat,
                longitude=lon,
                method="exif",
                confidence=0.95,
                source_text=image_path,
                metadata={
                    "altitude": self._get_altitude(gps_info),
                    "timestamp": str(gps_info.get("GPSDateStamp", "")),
                },
            )
        except ImportError:
            logger.warning("geoextractor.pillow_not_available")
            return None
        except Exception as e:
            logger.debug("geoextractor.exif_failed", path=image_path, error=str(e))
            return None

    @staticmethod
    def _gps_to_decimal(coords: tuple, ref: str) -> float:
        """Convert GPS EXIF coordinates to decimal degrees."""
        degrees = float(coords[0])
        minutes = float(coords[1])
        seconds = float(coords[2])
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal

    @staticmethod
    def _get_altitude(gps_info: dict[str, Any]) -> float | None:
        """Extract altitude from GPS info."""
        alt = gps_info.get("GPSAltitude")
        if alt is not None:
            alt_ref = gps_info.get("GPSAltitudeRef", 0)
            altitude = float(alt)
            if alt_ref == 1:
                altitude = -altitude
            return altitude
        return None

    @staticmethod
    def _deduplicate(
        results: list[GeoResult],
        threshold_km: float = 0.1,
    ) -> list[GeoResult]:
        """Remove near-duplicate results, keeping the highest confidence."""
        if len(results) <= 1:
            return results

        # Sort by confidence descending
        sorted_results = sorted(results, key=lambda r: r.confidence, reverse=True)
        kept: list[GeoResult] = []

        for result in sorted_results:
            is_duplicate = False
            for existing in kept:
                dist = _haversine_km(
                    result.latitude,
                    result.longitude,
                    existing.latitude,
                    existing.longitude,
                )
                if dist < threshold_km:
                    is_duplicate = True
                    break
            if not is_duplicate:
                kept.append(result)

        return kept

    def close(self) -> None:
        """Close the GeoIP reader if open."""
        if self._geoip_reader:
            self._geoip_reader.close()
            self._geoip_reader = None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

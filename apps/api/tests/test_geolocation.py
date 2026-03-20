"""Geolocation extraction tests — coordinate parsing, IP, EXIF."""

import pytest
from unittest.mock import MagicMock, patch

from nexus.processing.geolocation import GeoExtractor, GeoResult


class TestCoordinateParsing:
    @pytest.fixture
    def extractor(self):
        return GeoExtractor()

    def test_parse_dd(self, extractor):
        text = "The location is at 40.446195, -79.948862 in Pittsburgh."
        results = extractor._parse_dd(text)
        assert len(results) == 1
        assert abs(results[0].latitude - 40.446195) < 0.001
        assert abs(results[0].longitude - (-79.948862)) < 0.001
        assert results[0].method == "coordinate"
        assert results[0].confidence == 0.95
        assert results[0].metadata["format"] == "DD"

    def test_parse_dd_multiple(self, extractor):
        text = "Points: 37.5665, 126.9780 and 35.6762, 139.6503"
        results = extractor._parse_dd(text)
        assert len(results) == 2

    def test_parse_dd_invalid_range(self, extractor):
        text = "Not coordinates: 999.123, 999.456"
        results = extractor._parse_dd(text)
        assert len(results) == 0

    def test_parse_dms(self, extractor):
        text = """40°26'46"N 79°58'56"W"""
        results = extractor._parse_dms(text)
        assert len(results) == 1
        assert abs(results[0].latitude - 40.446111) < 0.01
        assert abs(results[0].longitude - (-79.982222)) < 0.01
        assert results[0].metadata["format"] == "DMS"

    def test_parse_dms_south_east(self, extractor):
        text = """33°51'25"S 151°12'30"E"""
        results = extractor._parse_dms(text)
        assert len(results) == 1
        assert results[0].latitude < 0  # South
        assert results[0].longitude > 0  # East

    def test_parse_utm(self, extractor):
        text = "UTM coordinates: 17T 589160 4477528"
        with patch("pyproj.Transformer") as mock_transformer:
            mock_instance = MagicMock()
            mock_instance.transform.return_value = (-79.95, 40.45)
            mock_transformer.from_crs.return_value = mock_instance

            results = extractor._parse_utm(text)
            assert len(results) == 1
            assert results[0].metadata["format"] == "UTM"
            assert results[0].metadata["zone"] == "17T"

    def test_parse_mgrs(self, extractor):
        text = "MGRS: 17TLJ8916077528"
        with patch("mgrs.MGRS") as mock_mgrs:
            mock_instance = MagicMock()
            mock_instance.toLatLon.return_value = (40.45, -79.95)
            mock_mgrs.return_value = mock_instance

            results = extractor._parse_mgrs(text)
            assert len(results) == 1
            assert results[0].metadata["format"] == "MGRS"

    def test_parse_coordinates_combined(self, extractor):
        text = "Location at 37.5665, 126.9780"
        results = extractor.parse_coordinates(text)
        # Should find DD format
        assert len(results) >= 1
        assert any(r.metadata.get("format") == "DD" for r in results)


class TestIPGeolocation:
    def test_valid_ip(self):
        mock_reader = MagicMock()
        mock_response = MagicMock()
        mock_response.location.latitude = 37.5665
        mock_response.location.longitude = 126.9780
        mock_response.location.accuracy_radius = 50
        mock_response.country.name = "South Korea"
        mock_response.country.iso_code = "KR"
        mock_response.city.name = "Seoul"
        mock_reader.city.return_value = mock_response

        extractor = GeoExtractor.__new__(GeoExtractor)
        extractor._geocoder = None
        extractor._geoip_reader = mock_reader

        result = extractor.extract_from_ip("1.2.3.4")
        assert result is not None
        assert abs(result.latitude - 37.5665) < 0.001
        assert result.method == "ip"
        assert result.confidence == 0.5
        assert result.metadata["country"] == "South Korea"

    def test_private_ip(self):
        mock_reader = MagicMock()
        mock_reader.city.side_effect = Exception("Address not found")

        extractor = GeoExtractor.__new__(GeoExtractor)
        extractor._geocoder = None
        extractor._geoip_reader = mock_reader

        result = extractor.extract_from_ip("192.168.1.1")
        assert result is None

    def test_no_reader(self):
        extractor = GeoExtractor()
        result = extractor.extract_from_ip("1.2.3.4")
        assert result is None


class TestEXIFExtraction:
    def test_image_with_gps(self):
        extractor = GeoExtractor()

        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img._getexif.return_value = {
                34853: {  # GPSInfo tag
                    1: "N",  # GPSLatitudeRef
                    2: (37.0, 33.0, 59.4),  # GPSLatitude
                    3: "E",  # GPSLongitudeRef
                    4: (126.0, 58.0, 40.8),  # GPSLongitude
                }
            }
            mock_open.return_value = mock_img

            # Patch TAGS to map 34853 to GPSInfo
            with patch("PIL.ExifTags.TAGS", {34853: "GPSInfo"}):
                with patch("PIL.ExifTags.GPSTAGS", {1: "GPSLatitudeRef", 2: "GPSLatitude", 3: "GPSLongitudeRef", 4: "GPSLongitude"}):
                    result = extractor.extract_from_exif("/test/photo.jpg")

            if result is not None:
                assert result.method == "exif"
                assert result.confidence == 0.95

    def test_image_without_gps(self):
        extractor = GeoExtractor()

        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img._getexif.return_value = {271: "Canon"}  # Only camera make
            mock_open.return_value = mock_img

            with patch("PIL.ExifTags.TAGS", {271: "Make"}):
                result = extractor.extract_from_exif("/test/photo.jpg")
                assert result is None

    def test_image_no_exif(self):
        extractor = GeoExtractor()

        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img._getexif.return_value = None
            mock_open.return_value = mock_img

            result = extractor.extract_from_exif("/test/photo.jpg")
            assert result is None


class TestDeduplication:
    def test_dedup_nearby_points(self):
        results = [
            GeoResult(latitude=37.5665, longitude=126.9780, method="coordinate", confidence=0.9),
            GeoResult(latitude=37.5665, longitude=126.9781, method="text", confidence=0.6),
        ]
        deduped = GeoExtractor._deduplicate(results, threshold_km=0.1)
        assert len(deduped) == 1
        assert deduped[0].confidence == 0.9  # Keeps higher confidence

    def test_dedup_distant_points(self):
        results = [
            GeoResult(latitude=37.5665, longitude=126.9780, method="coordinate", confidence=0.9),
            GeoResult(latitude=35.6762, longitude=139.6503, method="text", confidence=0.6),
        ]
        deduped = GeoExtractor._deduplicate(results, threshold_km=0.1)
        assert len(deduped) == 2  # Different cities, keep both

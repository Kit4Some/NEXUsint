"""GEOINT collector tests with mocked HTTP responses."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nexus.collectors.base import CollectionQuery
from nexus.collectors.geoint.geocoder_service import GeocoderService
from nexus.collectors.geoint.manager import GeointManager
from nexus.collectors.geoint.overpass_collector import OverpassCollector
from nexus.collectors.geoint.sentinel_collector import SentinelCollector


# --- Sentinel Collector Tests ---


class TestSentinelCollector:
    @pytest.fixture
    def collector(self):
        return SentinelCollector()

    @pytest.mark.asyncio
    async def test_search_products(self, collector):
        mock_response = {
            "value": [
                {
                    "Id": "product-123",
                    "Name": "S2A_MSIL2A_20240101",
                    "ContentDate": {"Start": "2024-01-01T10:00:00Z"},
                    "ContentLength": 1073741824,
                    "GeoFootprint": {
                        "coordinates": [[[126.0, 37.0], [127.0, 37.0], [127.0, 38.0], [126.0, 38.0], [126.0, 37.0]]]
                    },
                    "Attributes": [
                        {"Name": "cloudCover", "Value": 5.0},
                        {"Name": "resolution", "Value": "10m"},
                    ],
                }
            ]
        }

        with patch.object(collector, "_get_session") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            session = AsyncMock()
            session.get = MagicMock(return_value=mock_resp)
            mock_session.return_value = session

            cq = CollectionQuery(
                query="satellite_search",
                scan_type="satellite_search",
                options={
                    "bbox": {"south": 37.0, "west": 126.0, "north": 38.0, "east": 127.0},
                    "max_cloud_cover": 20.0,
                },
            )
            results = await collector.collect(cq)

            assert len(results) == 1
            assert results[0].source_int == "GEOINT"
            assert results[0].normalized["entity_type"] == "SatelliteImage"
            assert results[0].normalized["product_id"] == "product-123"
            assert results[0].reliability_grade == "B"

    @pytest.mark.asyncio
    async def test_health_check(self, collector):
        with patch.object(collector, "_get_session") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            session = AsyncMock()
            session.get = MagicMock(return_value=mock_resp)
            mock_session.return_value = session

            result = await collector.health_check()
            assert result is True


# --- Overpass Collector Tests ---


class TestOverpassCollector:
    @pytest.fixture
    def collector(self):
        return OverpassCollector()

    @pytest.mark.asyncio
    async def test_query_bbox(self, collector):
        mock_response = {
            "elements": [
                {
                    "type": "node",
                    "id": 12345,
                    "lat": 37.5665,
                    "lon": 126.9780,
                    "tags": {"name": "Seoul City Hall", "amenity": "government"},
                },
                {
                    "type": "way",
                    "id": 67890,
                    "center": {"lat": 37.5700, "lon": 126.9820},
                    "tags": {"name": "Gwanghwamun", "tourism": "attraction"},
                },
            ]
        }

        with patch.object(collector, "_execute_query", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_response

            cq = CollectionQuery(
                query="osm_features",
                scan_type="osm_bbox",
                options={
                    "bbox": {"south": 37.5, "west": 126.9, "north": 37.6, "east": 127.0},
                },
            )
            results = await collector.collect(cq)

            assert len(results) == 2
            assert results[0].normalized["entity_type"] == "GeoFeature"
            assert results[0].normalized["name"] == "Seoul City Hall"
            assert results[0].source_int == "GEOINT"

    @pytest.mark.asyncio
    async def test_health_check(self, collector):
        with patch.object(collector, "_get_session") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            session = AsyncMock()
            session.post = MagicMock(return_value=mock_resp)
            mock_session.return_value = session

            result = await collector.health_check()
            assert result is True


# --- Geocoder Service Tests ---


class TestGeocoderService:
    @pytest.fixture
    def collector(self):
        return GeocoderService()

    @pytest.mark.asyncio
    async def test_forward_geocode(self, collector):
        mock_response = [
            {
                "lat": "37.5665",
                "lon": "126.9780",
                "display_name": "Seoul, South Korea",
                "name": "Seoul",
                "osm_type": "relation",
                "osm_id": "2297418",
                "type": "city",
                "category": "place",
                "importance": 0.85,
                "boundingbox": ["37.4", "37.7", "126.7", "127.2"],
                "address": {
                    "city": "Seoul",
                    "country": "South Korea",
                    "country_code": "kr",
                    "state": "Seoul",
                },
            }
        ]

        with patch.object(collector, "_get_session") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            session = AsyncMock()
            session.get = MagicMock(return_value=mock_resp)
            mock_session.return_value = session

            results = await collector.forward_geocode("Seoul")

            assert len(results) == 1
            assert results[0].normalized["entity_type"] == "Location"
            assert results[0].normalized["latitude"] == 37.5665
            assert results[0].normalized["longitude"] == 126.978
            assert results[0].normalized["country"] == "South Korea"
            assert results[0].reliability_grade == "C"

    @pytest.mark.asyncio
    async def test_reverse_geocode(self, collector):
        mock_response = {
            "display_name": "Seoul City Hall, Seoul, South Korea",
            "name": "Seoul City Hall",
            "osm_type": "way",
            "osm_id": "12345",
            "type": "government",
            "category": "amenity",
            "address": {
                "city": "Seoul",
                "country": "South Korea",
                "country_code": "kr",
                "state": "Seoul",
            },
        }

        with patch.object(collector, "_get_session") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            session = AsyncMock()
            session.get = MagicMock(return_value=mock_resp)
            mock_session.return_value = session

            results = await collector.reverse_geocode(37.5665, 126.9780)

            assert len(results) == 1
            assert results[0].normalized["entity_type"] == "Location"
            assert results[0].normalized["city"] == "Seoul"


# --- Manager Tests ---


class TestGeointManager:
    @pytest.mark.asyncio
    async def test_routing_satellite(self):
        manager = GeointManager()
        with patch.object(manager.sentinel, "collect", new_callable=AsyncMock) as mock:
            mock.return_value = []
            await manager.collect("test", "satellite_search")
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_routing_osm(self):
        manager = GeointManager()
        with patch.object(manager.overpass, "collect", new_callable=AsyncMock) as mock:
            mock.return_value = []
            await manager.collect("test", "osm_bbox")
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_routing_geocode(self):
        manager = GeointManager()
        with patch.object(manager.geocoder, "collect", new_callable=AsyncMock) as mock:
            mock.return_value = []
            await manager.collect("Seoul", "geocode_forward")
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_parallel(self):
        manager = GeointManager()
        with (
            patch.object(manager.sentinel, "collect", new_callable=AsyncMock) as m1,
            patch.object(manager.overpass, "collect", new_callable=AsyncMock) as m2,
            patch.object(manager.geocoder, "collect", new_callable=AsyncMock) as m3,
        ):
            m1.return_value = []
            m2.return_value = []
            m3.return_value = []
            await manager.collect("test", "full")
            m1.assert_called_once()
            m2.assert_called_once()
            m3.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self):
        manager = GeointManager()
        with (
            patch.object(manager.sentinel, "health_check", new_callable=AsyncMock) as m1,
            patch.object(manager.overpass, "health_check", new_callable=AsyncMock) as m2,
            patch.object(manager.geocoder, "health_check", new_callable=AsyncMock) as m3,
        ):
            m1.return_value = True
            m2.return_value = True
            m3.return_value = False
            result = await manager.health_check()
            assert result == {"sentinel": True, "overpass": True, "geocoder": False}

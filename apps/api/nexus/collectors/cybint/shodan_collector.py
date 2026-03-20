"""Shodan API collector for IP/host intelligence."""

from datetime import datetime
from typing import Any

import shodan
import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()


class ShodanCollector(BaseCollector):
    """Collect IP and host intelligence from Shodan."""

    def __init__(self) -> None:
        super().__init__(rate_limit=1.0, max_retries=3)
        self._api = shodan.Shodan(settings.shodan_api_key)

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Collect data from Shodan based on scan type."""
        scan_type = query.scan_type
        results: list[CollectionResult] = []

        if scan_type == "host":
            results = await self._scan_host(query.query)
        elif scan_type == "search":
            results = await self._search(query.query)
        elif scan_type == "dns":
            results = await self._dns_resolve(query.query)
        else:
            results = await self._scan_host(query.query)

        logger.info("shodan.collected", scan_type=scan_type, result_count=len(results))
        return results

    async def _scan_host(self, ip: str) -> list[CollectionResult]:
        """Scan a specific IP address."""
        try:
            host = self._api.host(ip)
        except shodan.APIError as e:
            logger.error("shodan.host_error", ip=ip, error=str(e))
            return []

        normalized = {
            "entity_type": "IPAddress",
            "address": host.get("ip_str", ip),
            "asn": host.get("asn", ""),
            "org": host.get("org", ""),
            "isp": host.get("isp", ""),
            "country": host.get("country_code", ""),
            "city": host.get("city", ""),
            "latitude": host.get("latitude"),
            "longitude": host.get("longitude"),
            "os": host.get("os"),
            "ports": host.get("ports", []),
            "hostnames": host.get("hostnames", []),
            "vulns": host.get("vulns", []),
            "services": [
                {
                    "port": svc.get("port"),
                    "transport": svc.get("transport"),
                    "product": svc.get("product", ""),
                    "version": svc.get("version", ""),
                    "banner": svc.get("data", "")[:500],
                }
                for svc in host.get("data", [])
            ],
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"shodan:host:{ip}",
                raw_data=host,
                normalized=normalized,
                metadata={"collector": "shodan", "scan_type": "host"},
                reliability_grade="B",
            )
        ]

    async def _search(self, query_str: str) -> list[CollectionResult]:
        """Search Shodan with a query string."""
        try:
            results = self._api.search(query_str, limit=100)
        except shodan.APIError as e:
            logger.error("shodan.search_error", query=query_str, error=str(e))
            return []

        collection_results = []
        for match in results.get("matches", []):
            normalized = {
                "entity_type": "IPAddress",
                "address": match.get("ip_str", ""),
                "port": match.get("port"),
                "transport": match.get("transport", ""),
                "product": match.get("product", ""),
                "version": match.get("version", ""),
                "org": match.get("org", ""),
                "country": match.get("location", {}).get("country_code", ""),
                "hostnames": match.get("hostnames", []),
            }

            collection_results.append(
                CollectionResult(
                    source_int="CYBINT",
                    source_id=f"shodan:search:{match.get('ip_str')}:{match.get('port')}",
                    raw_data=match,
                    normalized=normalized,
                    metadata={"collector": "shodan", "scan_type": "search", "query": query_str},
                    reliability_grade="B",
                )
            )

        return collection_results

    async def _dns_resolve(self, domain: str) -> list[CollectionResult]:
        """Resolve DNS for a domain via Shodan."""
        try:
            dns_result = self._api.dns.domain_info(domain)
        except shodan.APIError as e:
            logger.error("shodan.dns_error", domain=domain, error=str(e))
            return []

        normalized = {
            "entity_type": "Domain",
            "domain": domain,
            "subdomains": dns_result.get("subdomains", []),
            "records": dns_result.get("data", []),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"shodan:dns:{domain}",
                raw_data=dns_result,
                normalized=normalized,
                metadata={"collector": "shodan", "scan_type": "dns"},
                reliability_grade="B",
            )
        ]

    async def health_check(self) -> bool:
        """Check if Shodan API is reachable."""
        try:
            info = self._api.info()
            return info.get("query_credits", 0) > 0
        except Exception:
            return False

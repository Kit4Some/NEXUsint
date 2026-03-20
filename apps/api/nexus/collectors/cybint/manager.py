"""CYBINT collection manager — orchestrates all CYBINT collectors."""

import asyncio
from typing import Any

import structlog

from nexus.collectors.base import CollectionQuery, CollectionResult
from nexus.collectors.cybint.shodan_collector import ShodanCollector
from nexus.collectors.cybint.dns_collector import DNSCollector
from nexus.collectors.cybint.certificate_collector import CertificateCollector
from nexus.collectors.cybint.threat_intel_collector import ThreatIntelCollector

logger = structlog.get_logger()


class CybintManager:
    """Orchestrates CYBINT data collection across all sub-collectors."""

    def __init__(self) -> None:
        self.shodan = ShodanCollector()
        self.dns = DNSCollector()
        self.certificate = CertificateCollector()
        self.threat_intel = ThreatIntelCollector()

    async def collect(
        self, query: str, scan_type: str, options: dict[str, Any] | None = None
    ) -> list[CollectionResult]:
        """Run appropriate collectors based on scan type."""
        cq = CollectionQuery(query=query, scan_type=scan_type, options=options or {})
        results: list[CollectionResult] = []

        if scan_type == "full":
            # Run all collectors in parallel
            tasks = [
                self.shodan.collect(CollectionQuery(query=query, scan_type="host")),
                self.dns.collect(CollectionQuery(query=query, scan_type="full")),
                self.certificate.collect(cq),
                self.threat_intel.collect(CollectionQuery(query=query, scan_type="domain")),
            ]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for result in gathered:
                if isinstance(result, list):
                    results.extend(result)
                elif isinstance(result, Exception):
                    logger.error("cybint.collector_failed", error=str(result))

        elif scan_type in ("host", "search"):
            results.extend(await self.shodan.collect(cq))

        elif scan_type in ("whois", "dns_records", "subdomains", "dns"):
            actual_type = "full" if scan_type == "dns" else scan_type
            results.extend(
                await self.dns.collect(CollectionQuery(query=query, scan_type=actual_type))
            )

        elif scan_type in ("certificates", "ct_log"):
            results.extend(await self.certificate.collect(cq))

        elif scan_type in ("ip", "ip_report", "domain", "domain_report", "hash", "file_report", "url"):
            results.extend(await self.threat_intel.collect(cq))

        else:
            # Default: try all relevant collectors
            results.extend(await self.dns.collect(CollectionQuery(query=query, scan_type="full")))
            results.extend(await self.certificate.collect(cq))

        logger.info(
            "cybint.collection_complete",
            query=query,
            scan_type=scan_type,
            total_results=len(results),
        )
        return results

    async def health_check(self) -> dict[str, bool]:
        """Check health of all CYBINT collectors."""
        checks = await asyncio.gather(
            self.shodan.health_check(),
            self.dns.health_check(),
            self.certificate.health_check(),
            self.threat_intel.health_check(),
            return_exceptions=True,
        )

        return {
            "shodan": checks[0] if isinstance(checks[0], bool) else False,
            "dns": checks[1] if isinstance(checks[1], bool) else False,
            "certificate": checks[2] if isinstance(checks[2], bool) else False,
            "threat_intel": checks[3] if isinstance(checks[3], bool) else False,
        }

    async def close(self) -> None:
        """Close all collector sessions."""
        await asyncio.gather(
            self.shodan.close(),
            self.dns.close(),
            self.certificate.close(),
            self.threat_intel.close(),
        )

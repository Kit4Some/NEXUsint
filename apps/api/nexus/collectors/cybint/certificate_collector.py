"""Certificate Transparency log collector via crt.sh."""

from datetime import datetime
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult

logger = structlog.get_logger()


class CertificateCollector(BaseCollector):
    """Collect SSL/TLS certificate data from Certificate Transparency logs."""

    CRT_SH_BASE = "https://crt.sh"

    def __init__(self) -> None:
        super().__init__(rate_limit=2.0, max_retries=3)

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Query crt.sh for certificate data related to a domain."""
        domain = query.query
        results: list[CollectionResult] = []

        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.CRT_SH_BASE}/?q={domain}&output=json",
            )
        except Exception as e:
            logger.error("certificate.crtsh_error", domain=domain, error=str(e))
            return []

        if not isinstance(data, list):
            return []

        seen_serials: set[str] = set()

        for entry in data:
            serial = str(entry.get("serial_number", ""))
            if serial in seen_serials:
                continue
            seen_serials.add(serial)

            normalized = {
                "entity_type": "Certificate",
                "serial_number": serial,
                "issuer_name": entry.get("issuer_name", ""),
                "common_name": entry.get("common_name", ""),
                "name_value": entry.get("name_value", ""),
                "not_before": entry.get("not_before", ""),
                "not_after": entry.get("not_after", ""),
                "entry_timestamp": entry.get("entry_timestamp", ""),
                "issuer_ca_id": entry.get("issuer_ca_id"),
            }

            results.append(
                CollectionResult(
                    source_int="CYBINT",
                    source_id=f"crtsh:cert:{serial}",
                    raw_data=entry,
                    normalized=normalized,
                    metadata={
                        "collector": "certificate",
                        "scan_type": "ct_log",
                        "domain": domain,
                    },
                    reliability_grade="A",
                )
            )

        logger.info("certificate.collected", domain=domain, cert_count=len(results))
        return results

    async def health_check(self) -> bool:
        """Check if crt.sh is reachable."""
        try:
            await self._request_with_retry("GET", f"{self.CRT_SH_BASE}/?q=example.com&output=json")
            return True
        except Exception:
            return False

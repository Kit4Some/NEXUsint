"""Threat intelligence feed collector — VirusTotal, AbuseIPDB, AlienVault OTX."""

from datetime import datetime
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()


class ThreatIntelCollector(BaseCollector):
    """Aggregate threat intelligence from multiple sources."""

    VT_BASE = "https://www.virustotal.com/api/v3"
    ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2"
    OTX_BASE = "https://otx.alienvault.com/api/v1"

    def __init__(self) -> None:
        super().__init__(rate_limit=4.0, max_retries=3)

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Collect threat intelligence for an IP, domain, or hash."""
        scan_type = query.scan_type
        target = query.query
        results: list[CollectionResult] = []

        if scan_type in ("ip", "ip_report"):
            results.extend(await self._vt_ip_report(target))
            results.extend(await self._abuseipdb_check(target))
            results.extend(await self._otx_ip_report(target))
        elif scan_type in ("domain", "domain_report"):
            results.extend(await self._vt_domain_report(target))
            results.extend(await self._otx_domain_report(target))
        elif scan_type in ("hash", "file_report"):
            results.extend(await self._vt_file_report(target))
        elif scan_type == "url":
            results.extend(await self._vt_url_report(target))
        else:
            # Auto-detect type
            if self._is_ip(target):
                results.extend(await self._vt_ip_report(target))
                results.extend(await self._abuseipdb_check(target))
            else:
                results.extend(await self._vt_domain_report(target))

        logger.info("threat_intel.collected", target=target, result_count=len(results))
        return results

    def _is_ip(self, value: str) -> bool:
        """Simple check if a string looks like an IP address."""
        parts = value.split(".")
        if len(parts) == 4:
            return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
        return ":" in value  # IPv6

    async def _vt_ip_report(self, ip: str) -> list[CollectionResult]:
        """Get VirusTotal IP address report."""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.VT_BASE}/ip_addresses/{ip}",
                headers={"x-apikey": settings.virustotal_api_key},
            )
        except Exception as e:
            logger.error("vt.ip_error", ip=ip, error=str(e))
            return []

        attrs = data.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        normalized = {
            "entity_type": "IPAddress",
            "address": ip,
            "country": attrs.get("country", ""),
            "as_owner": attrs.get("as_owner", ""),
            "asn": attrs.get("asn"),
            "network": attrs.get("network", ""),
            "reputation": attrs.get("reputation", 0),
            "malicious_count": stats.get("malicious", 0),
            "suspicious_count": stats.get("suspicious", 0),
            "harmless_count": stats.get("harmless", 0),
            "total_votes_malicious": attrs.get("total_votes", {}).get("malicious", 0),
        }

        grade = "C" if stats.get("malicious", 0) > 5 else "B"

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"virustotal:ip:{ip}",
                raw_data=data.get("data", {}),
                normalized=normalized,
                metadata={"collector": "virustotal", "scan_type": "ip_report"},
                reliability_grade=grade,
            )
        ]

    async def _vt_domain_report(self, domain: str) -> list[CollectionResult]:
        """Get VirusTotal domain report."""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.VT_BASE}/domains/{domain}",
                headers={"x-apikey": settings.virustotal_api_key},
            )
        except Exception as e:
            logger.error("vt.domain_error", domain=domain, error=str(e))
            return []

        attrs = data.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        normalized = {
            "entity_type": "Domain",
            "name": domain,
            "registrar": attrs.get("registrar", ""),
            "creation_date": attrs.get("creation_date", ""),
            "reputation": attrs.get("reputation", 0),
            "malicious_count": stats.get("malicious", 0),
            "categories": attrs.get("categories", {}),
            "dns_records": attrs.get("last_dns_records", []),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"virustotal:domain:{domain}",
                raw_data=data.get("data", {}),
                normalized=normalized,
                metadata={"collector": "virustotal", "scan_type": "domain_report"},
                reliability_grade="B",
            )
        ]

    async def _vt_file_report(self, file_hash: str) -> list[CollectionResult]:
        """Get VirusTotal file/hash report."""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.VT_BASE}/files/{file_hash}",
                headers={"x-apikey": settings.virustotal_api_key},
            )
        except Exception as e:
            logger.error("vt.file_error", hash=file_hash, error=str(e))
            return []

        attrs = data.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        normalized = {
            "entity_type": "Indicator",
            "indicator_type": "file_hash",
            "value": file_hash,
            "name": attrs.get("meaningful_name", ""),
            "type_description": attrs.get("type_description", ""),
            "size": attrs.get("size"),
            "sha256": attrs.get("sha256", ""),
            "md5": attrs.get("md5", ""),
            "malicious_count": stats.get("malicious", 0),
            "detection_names": list(
                v.get("result", "")
                for v in attrs.get("last_analysis_results", {}).values()
                if v.get("category") == "malicious" and v.get("result")
            )[:20],
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"virustotal:file:{file_hash}",
                raw_data=data.get("data", {}),
                normalized=normalized,
                metadata={"collector": "virustotal", "scan_type": "file_report"},
                reliability_grade="B",
            )
        ]

    async def _vt_url_report(self, url: str) -> list[CollectionResult]:
        """Get VirusTotal URL report."""
        import base64

        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.VT_BASE}/urls/{url_id}",
                headers={"x-apikey": settings.virustotal_api_key},
            )
        except Exception as e:
            logger.error("vt.url_error", url=url, error=str(e))
            return []

        attrs = data.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        normalized = {
            "entity_type": "Indicator",
            "indicator_type": "url",
            "value": url,
            "malicious_count": stats.get("malicious", 0),
            "categories": attrs.get("categories", {}),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"virustotal:url:{url_id}",
                raw_data=data.get("data", {}),
                normalized=normalized,
                metadata={"collector": "virustotal", "scan_type": "url_report"},
                reliability_grade="B",
            )
        ]

    async def _abuseipdb_check(self, ip: str) -> list[CollectionResult]:
        """Check IP reputation via AbuseIPDB."""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.ABUSEIPDB_BASE}/check",
                headers={
                    "Key": settings.abuseipdb_api_key,
                    "Accept": "application/json",
                },
                params={"ipAddress": ip, "maxAgeInDays": "90", "verbose": ""},
            )
        except Exception as e:
            logger.error("abuseipdb.error", ip=ip, error=str(e))
            return []

        report = data.get("data", {})
        normalized = {
            "entity_type": "IPAddress",
            "address": ip,
            "abuse_confidence_score": report.get("abuseConfidenceScore", 0),
            "country": report.get("countryCode", ""),
            "isp": report.get("isp", ""),
            "domain": report.get("domain", ""),
            "total_reports": report.get("totalReports", 0),
            "is_whitelisted": report.get("isWhitelisted", False),
            "usage_type": report.get("usageType", ""),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"abuseipdb:{ip}",
                raw_data=report,
                normalized=normalized,
                metadata={"collector": "abuseipdb", "scan_type": "ip_check"},
                reliability_grade="B",
            )
        ]

    async def _otx_ip_report(self, ip: str) -> list[CollectionResult]:
        """Get AlienVault OTX IP reputation."""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.OTX_BASE}/indicators/IPv4/{ip}/general",
                headers={"X-OTX-API-KEY": settings.alienvault_otx_api_key},
            )
        except Exception as e:
            logger.error("otx.ip_error", ip=ip, error=str(e))
            return []

        normalized = {
            "entity_type": "IPAddress",
            "address": ip,
            "reputation": data.get("reputation", 0),
            "pulse_count": data.get("pulse_info", {}).get("count", 0),
            "country": data.get("country_name", ""),
            "asn": data.get("asn", ""),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"otx:ip:{ip}",
                raw_data=data,
                normalized=normalized,
                metadata={"collector": "alienvault_otx", "scan_type": "ip_report"},
                reliability_grade="C",
            )
        ]

    async def _otx_domain_report(self, domain: str) -> list[CollectionResult]:
        """Get AlienVault OTX domain report."""
        try:
            data = await self._request_with_retry(
                "GET",
                f"{self.OTX_BASE}/indicators/domain/{domain}/general",
                headers={"X-OTX-API-KEY": settings.alienvault_otx_api_key},
            )
        except Exception as e:
            logger.error("otx.domain_error", domain=domain, error=str(e))
            return []

        normalized = {
            "entity_type": "Domain",
            "name": domain,
            "pulse_count": data.get("pulse_info", {}).get("count", 0),
            "alexa": data.get("alexa", ""),
            "whois": data.get("whois", ""),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"otx:domain:{domain}",
                raw_data=data,
                normalized=normalized,
                metadata={"collector": "alienvault_otx", "scan_type": "domain_report"},
                reliability_grade="C",
            )
        ]

    async def health_check(self) -> bool:
        """Check if threat intel APIs are reachable."""
        try:
            await self._request_with_retry(
                "GET",
                f"{self.VT_BASE}/ip_addresses/8.8.8.8",
                headers={"x-apikey": settings.virustotal_api_key},
            )
            return True
        except Exception:
            return False

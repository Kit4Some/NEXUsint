"""DNS and WHOIS data collector."""

from datetime import datetime
from typing import Any

import aiodns
import whois
import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()


class DNSCollector(BaseCollector):
    """Collect DNS records, WHOIS data, and subdomain information."""

    def __init__(self) -> None:
        super().__init__(rate_limit=5.0, max_retries=3)
        self._resolver = aiodns.DNSResolver()

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Collect DNS-related data for a domain or IP."""
        scan_type = query.scan_type
        results: list[CollectionResult] = []

        if scan_type == "whois":
            results = await self._whois_lookup(query.query)
        elif scan_type == "dns_records":
            results = await self._dns_records(query.query)
        elif scan_type == "subdomains":
            results = await self._enumerate_subdomains(query.query)
        elif scan_type == "full":
            whois_r = await self._whois_lookup(query.query)
            dns_r = await self._dns_records(query.query)
            sub_r = await self._enumerate_subdomains(query.query)
            results = whois_r + dns_r + sub_r
        else:
            results = await self._dns_records(query.query)

        logger.info("dns.collected", scan_type=scan_type, result_count=len(results))
        return results

    async def _whois_lookup(self, domain: str) -> list[CollectionResult]:
        """Perform WHOIS lookup."""
        try:
            w = whois.whois(domain)
        except Exception as e:
            logger.error("dns.whois_error", domain=domain, error=str(e))
            return []

        raw_data = {}
        for key in [
            "domain_name", "registrar", "whois_server", "creation_date",
            "expiration_date", "updated_date", "name_servers", "status",
            "emails", "registrant", "registrant_country", "org",
        ]:
            val = getattr(w, key, None)
            if val is not None:
                if isinstance(val, datetime):
                    raw_data[key] = val.isoformat()
                elif isinstance(val, list):
                    raw_data[key] = [
                        v.isoformat() if isinstance(v, datetime) else str(v) for v in val
                    ]
                else:
                    raw_data[key] = str(val)

        normalized = {
            "entity_type": "Domain",
            "name": domain,
            "registrar": raw_data.get("registrar", ""),
            "registrant": raw_data.get("org", raw_data.get("registrant", "")),
            "registrant_country": raw_data.get("registrant_country", ""),
            "creation_date": raw_data.get("creation_date", ""),
            "expiration_date": raw_data.get("expiration_date", ""),
            "name_servers": raw_data.get("name_servers", []),
            "emails": raw_data.get("emails", []),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"whois:{domain}",
                raw_data=raw_data,
                normalized=normalized,
                metadata={"collector": "dns", "scan_type": "whois"},
                reliability_grade="B",
            )
        ]

    async def _dns_records(self, domain: str) -> list[CollectionResult]:
        """Query DNS records (A, AAAA, MX, NS, TXT, CNAME)."""
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]
        all_records: dict[str, list[str]] = {}

        for rtype in record_types:
            try:
                result = await self._resolver.query(domain, rtype)
                if rtype == "MX":
                    all_records[rtype] = [
                        f"{r.priority} {r.host}" for r in result
                    ]
                elif rtype == "TXT":
                    all_records[rtype] = [str(r.text) for r in result]
                elif rtype == "NS":
                    all_records[rtype] = [str(r.host) for r in result]
                elif rtype == "CNAME":
                    all_records[rtype] = [str(r.cname) for r in result]
                else:
                    all_records[rtype] = [str(r.host) for r in result]
            except aiodns.error.DNSError:
                pass
            except Exception as e:
                logger.debug("dns.record_error", domain=domain, rtype=rtype, error=str(e))

        normalized = {
            "entity_type": "Domain",
            "name": domain,
            "records": all_records,
            "ip_addresses": all_records.get("A", []) + all_records.get("AAAA", []),
            "mail_servers": all_records.get("MX", []),
            "name_servers": all_records.get("NS", []),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"dns:records:{domain}",
                raw_data=all_records,
                normalized=normalized,
                metadata={"collector": "dns", "scan_type": "dns_records"},
                reliability_grade="A",
            )
        ]

    async def _enumerate_subdomains(self, domain: str) -> list[CollectionResult]:
        """Enumerate subdomains via crt.sh Certificate Transparency logs."""
        await self._rate_limit_wait()

        try:
            data = await self._request_with_retry(
                "GET",
                f"https://crt.sh/?q=%.{domain}&output=json",
            )
        except Exception as e:
            logger.error("dns.crtsh_error", domain=domain, error=str(e))
            return []

        subdomains: set[str] = set()
        for entry in data if isinstance(data, list) else []:
            name_value = entry.get("name_value", "")
            for name in name_value.split("\n"):
                name = name.strip().lower()
                if name.endswith(domain) and "*" not in name:
                    subdomains.add(name)

        normalized = {
            "entity_type": "Domain",
            "parent_domain": domain,
            "subdomains": sorted(subdomains),
            "subdomain_count": len(subdomains),
        }

        return [
            CollectionResult(
                source_int="CYBINT",
                source_id=f"crtsh:subdomains:{domain}",
                raw_data={"subdomains": sorted(subdomains), "source": "crt.sh"},
                normalized=normalized,
                metadata={"collector": "dns", "scan_type": "subdomains"},
                reliability_grade="B",
            )
        ]

    async def health_check(self) -> bool:
        """Check if DNS resolution is working."""
        try:
            await self._resolver.query("google.com", "A")
            return True
        except Exception:
            return False

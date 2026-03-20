"""3-Tier Named Entity Recognition pipeline.

Tier 1 (Base): spaCy — PERSON, ORG, GPE, DATE, LOC, NORP, FAC
Tier 2 (Domain): SecBERT + GLiNER — THREAT_ACTOR, MALWARE, TOOL, ATTACK_PATTERN, CAMPAIGN, VULNERABILITY, INTRUSION_SET
Tier 3 (Pattern): Regex — IPv4/v6, email, domain, URL, crypto wallets, CVE, hashes, MMSI, ICAO24
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class NEREntity:
    """A named entity extracted from text."""

    text: str
    label: str
    start: int
    end: int
    confidence: float
    tier: int
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "tier": self.tier,
            "source": self.source,
        }


# Tier 3: Regex patterns for OSINT-relevant entities
PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("IPV4", "IPAddress", re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    )),
    ("IPV6", "IPAddress", re.compile(
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
        r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b"
        r"|\b::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}\b"
    )),
    ("EMAIL", "Email", re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    )),
    ("DOMAIN", "Domain", re.compile(
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
    )),
    ("URL", "URL", re.compile(
        r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"
    )),
    ("CVE", "Vulnerability", re.compile(
        r"\bCVE-\d{4}-\d{4,}\b"
    )),
    ("MD5", "Hash", re.compile(
        r"\b[a-fA-F0-9]{32}\b"
    )),
    ("SHA1", "Hash", re.compile(
        r"\b[a-fA-F0-9]{40}\b"
    )),
    ("SHA256", "Hash", re.compile(
        r"\b[a-fA-F0-9]{64}\b"
    )),
    ("BTC_WALLET", "CryptoWallet", re.compile(
        r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|bc1[a-zA-HJ-NP-Z0-9]{39,59}\b"
    )),
    ("ETH_WALLET", "CryptoWallet", re.compile(
        r"\b0x[a-fA-F0-9]{40}\b"
    )),
    ("MMSI", "Vessel", re.compile(
        r"\bMMSI[:\s]?\d{9}\b", re.IGNORECASE
    )),
    ("ICAO24", "Aircraft", re.compile(
        r"\bICAO24[:\s]?[a-fA-F0-9]{6}\b", re.IGNORECASE
    )),
    ("PHONE", "PhoneNumber", re.compile(
        r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    )),
]

# spaCy label → our label mapping
SPACY_LABEL_MAP = {
    "PERSON": "Person",
    "ORG": "Organization",
    "GPE": "Location",
    "LOC": "Location",
    "FAC": "Location",
    "DATE": "Date",
    "TIME": "Time",
    "NORP": "Group",
    "EVENT": "Event",
    "PRODUCT": "Object",
    "MONEY": "Financial",
}


class NERPipeline:
    """3-tier NER pipeline for OSINT entity extraction."""

    def __init__(self) -> None:
        self._nlp = None  # Lazy-loaded
        self._domain_ner = None  # Lazy-loaded Tier 2

    def _load_spacy(self):
        """Lazy-load spaCy model."""
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("ner.spacy_model_missing, falling back to blank")
                self._nlp = spacy.blank("en")
        return self._nlp

    def extract(self, text: str, source: str = "") -> list[NEREntity]:
        """Extract entities from text using all tiers."""
        entities: list[NEREntity] = []

        # Tier 1: spaCy NER
        tier1 = self._tier1_spacy(text, source)
        entities.extend(tier1)

        # Tier 2: Domain-specific NER (SecBERT + GLiNER)
        tier2 = self._tier2_domain(text, source)
        entities.extend(tier2)

        # Tier 3: Regex patterns
        tier3 = self._tier3_patterns(text, source)
        entities.extend(tier3)

        # Deduplicate: prefer more specific (higher tier) and higher confidence
        entities = self._deduplicate(entities)

        return entities

    def extract_batch(self, texts: list[tuple[str, str]]) -> list[list[NEREntity]]:
        """Extract entities from multiple texts. Each item is (text, source_id)."""
        return [self.extract(text, source) for text, source in texts]

    def _tier1_spacy(self, text: str, source: str) -> list[NEREntity]:
        """Tier 1: spaCy base NER."""
        nlp = self._load_spacy()
        doc = nlp(text)
        entities = []

        for ent in doc.ents:
            label = SPACY_LABEL_MAP.get(ent.label_, ent.label_)
            entities.append(
                NEREntity(
                    text=ent.text,
                    label=label,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.7,
                    tier=1,
                    source=source,
                )
            )

        return entities

    def _tier2_domain(self, text: str, source: str) -> list[NEREntity]:
        """Tier 2: Domain-specific NER using SecBERT and GLiNER."""
        if self._domain_ner is None:
            try:
                from nexus.processing.ner_domain import DomainNER
                self._domain_ner = DomainNER()
            except Exception as e:
                logger.warning("ner.domain_ner_unavailable", error=str(e))
                return []

        try:
            results = self._domain_ner.extract(text, source)
            return [
                NEREntity(
                    text=r["text"],
                    label=r["label"],
                    start=r["start"],
                    end=r["end"],
                    confidence=r["confidence"],
                    tier=r["tier"],
                    source=r.get("source", source),
                )
                for r in results
            ]
        except Exception as e:
            logger.warning("ner.tier2_error", error=str(e))
            return []

    def _tier3_patterns(self, text: str, source: str) -> list[NEREntity]:
        """Tier 3: Regex pattern matching for technical indicators."""
        entities = []

        for pattern_name, label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    NEREntity(
                        text=match.group(),
                        label=label,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.95,
                        tier=3,
                        source=source,
                    )
                )

        return entities

    def _deduplicate(self, entities: list[NEREntity]) -> list[NEREntity]:
        """Deduplicate entities, preferring higher tier and confidence."""
        seen: dict[str, NEREntity] = {}

        for entity in entities:
            key = f"{entity.text}:{entity.start}:{entity.end}"
            if key not in seen:
                seen[key] = entity
            else:
                existing = seen[key]
                # Prefer higher tier (more specific) and higher confidence
                if entity.tier > existing.tier or (
                    entity.tier == existing.tier and entity.confidence > existing.confidence
                ):
                    seen[key] = entity

        return list(seen.values())

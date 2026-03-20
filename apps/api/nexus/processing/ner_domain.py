"""Tier 2 domain-specific NER using SecBERT and GLiNER.

Extracts cybersecurity entities: THREAT_ACTOR, MALWARE, TOOL, ATTACK_PATTERN,
CAMPAIGN, VULNERABILITY, INTRUSION_SET.

Falls back gracefully if models are unavailable.
"""

import structlog

logger = structlog.get_logger()

# Domain entity labels for zero-shot extraction
CYBER_LABELS = [
    "threat actor",
    "malware",
    "hacking tool",
    "attack pattern",
    "campaign",
    "vulnerability",
    "intrusion set",
]

LABEL_MAP = {
    "threat actor": "ThreatActor",
    "malware": "Malware",
    "hacking tool": "Tool",
    "attack pattern": "AttackPattern",
    "campaign": "Campaign",
    "vulnerability": "Vulnerability",
    "intrusion set": "IntrusionSet",
}


class DomainNER:
    """Domain-specific NER for cybersecurity text using transformer models."""

    def __init__(self):
        self._secbert_pipeline = None
        self._gliner_model = None
        self._secbert_available = False
        self._gliner_available = False
        self._init_attempted = False

    def _init_models(self):
        """Lazy-load models. Gracefully handles missing dependencies."""
        if self._init_attempted:
            return
        self._init_attempted = True

        # Try SecBERT
        try:
            from transformers import pipeline

            self._secbert_pipeline = pipeline(
                "ner",
                model="jackaduma/SecBERT",
                aggregation_strategy="simple",
                device=-1,  # CPU
            )
            self._secbert_available = True
            logger.info("ner_domain.secbert_loaded")
        except Exception as e:
            logger.warning("ner_domain.secbert_unavailable", error=str(e))

        # Try GLiNER
        try:
            from gliner import GLiNER

            self._gliner_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
            self._gliner_available = True
            logger.info("ner_domain.gliner_loaded")
        except Exception as e:
            logger.warning("ner_domain.gliner_unavailable", error=str(e))

    def extract(
        self, text: str, source: str = "", custom_labels: list[str] | None = None,
    ) -> list[dict]:
        """Extract domain-specific entities from text.

        Args:
            text: Input text to analyze.
            source: Source identifier for provenance.
            custom_labels: Optional custom entity labels for GLiNER zero-shot.

        Returns:
            List of entity dicts with text, label, start, end, confidence, tier, source.
        """
        self._init_models()
        entities = []

        # SecBERT NER
        if self._secbert_available and self._secbert_pipeline:
            try:
                results = self._secbert_pipeline(text[:512])
                for r in results:
                    if r.get("score", 0) >= 0.5:
                        mapped_label = self._map_secbert_label(r.get("entity_group", ""))
                        if mapped_label:
                            entities.append({
                                "text": r["word"],
                                "label": mapped_label,
                                "start": r.get("start", 0),
                                "end": r.get("end", 0),
                                "confidence": round(r["score"], 3),
                                "tier": 2,
                                "source": source,
                            })
            except Exception as e:
                logger.warning("ner_domain.secbert_error", error=str(e))

        # GLiNER zero-shot NER
        if self._gliner_available and self._gliner_model:
            try:
                labels = custom_labels or CYBER_LABELS
                results = self._gliner_model.predict_entities(
                    text[:1024], labels, threshold=0.4,
                )
                for r in results:
                    mapped = LABEL_MAP.get(r["label"], r["label"])
                    # Avoid duplicates from SecBERT
                    if not any(
                        e["text"] == r["text"] and e["start"] == r["start"]
                        for e in entities
                    ):
                        entities.append({
                            "text": r["text"],
                            "label": mapped,
                            "start": r.get("start", 0),
                            "end": r.get("end", 0),
                            "confidence": round(r.get("score", 0.5), 3),
                            "tier": 2,
                            "source": source,
                        })
            except Exception as e:
                logger.warning("ner_domain.gliner_error", error=str(e))

        return entities

    @staticmethod
    def _map_secbert_label(label: str) -> str | None:
        """Map SecBERT NER labels to our domain labels."""
        mapping = {
            "MISC": None,  # too generic
            "PER": "ThreatActor",
            "ORG": "ThreatActor",  # in security context, ORG often = threat group
            "LOC": None,  # handled by Tier 1
        }
        return mapping.get(label)

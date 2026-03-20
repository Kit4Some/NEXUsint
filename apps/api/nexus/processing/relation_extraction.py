"""3-pass relation extraction — LLM-based with rule-based fallback."""

import json
import re
from dataclasses import dataclass
from typing import Any

import structlog

from nexus.processing.ner import NEREntity

logger = structlog.get_logger()

RELATIONSHIP_TYPES = [
    "AFFILIATED_WITH", "TARGETS", "USES", "COMMUNICATES_WITH",
    "LOCATED_AT", "MEMBER_OF", "OWNS", "OPERATES", "REGISTERED_BY",
    "ATTRIBUTED_TO", "HOSTS", "RESOLVES_TO", "PART_OF",
]

EVENT_TYPES = [
    "ATTACK", "MOVEMENT", "COMMUNICATION", "REGISTRATION",
    "SIGHTING", "TRANSACTION", "MEETING", "PUBLICATION",
]

TEMPORAL_TYPES = ["BEFORE", "AFTER", "DURING", "SIMULTANEOUS"]
SPATIAL_TYPES = ["NEAR", "WITHIN", "DEPARTS_FROM", "ARRIVES_AT"]

PASS1_PROMPT = """Extract relationships between entities in the following text.
Entities found: {entities}

Text: {text}

For each relationship, output a JSON array with objects containing:
- "source": entity text
- "target": entity text
- "type": one of {rel_types}
- "confidence": float 0.0-1.0
- "evidence": the sentence supporting this relationship

Output ONLY valid JSON array. If no relationships found, output [].
"""

PASS2_PROMPT = """Extract events from the following text.
Known entities: {entities}

Text: {text}

For each event, output a JSON array with objects containing:
- "type": one of {event_types}
- "who": entity involved (or null)
- "what": description
- "when": timestamp or date reference (or null)
- "where": location (or null)
- "confidence": float 0.0-1.0
- "evidence": supporting sentence

Output ONLY valid JSON array. If no events found, output [].
"""

PASS3_PROMPT = """Analyze temporal and spatial relationships between entities and events.
Entities: {entities}

Text: {text}

For each temporal/spatial relationship, output a JSON array with objects containing:
- "source": entity or event text
- "target": entity or event text
- "type": one of {types}
- "confidence": float 0.0-1.0
- "context": brief explanation

Output ONLY valid JSON array. If none found, output [].
"""


@dataclass
class ExtractedRelation:
    """A relationship extracted from text."""

    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float
    evidence_text: str
    extraction_method: str  # "llm" or "rule"
    temporal_context: str | None = None
    spatial_context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "evidence_text": self.evidence_text,
            "extraction_method": self.extraction_method,
            "temporal_context": self.temporal_context,
            "spatial_context": self.spatial_context,
        }


class RelationExtractor:
    """3-pass relation extraction using LLM with rule-based fallback."""

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    async def extract(
        self, text: str, entities: list[NEREntity], source: str = ""
    ) -> list[ExtractedRelation]:
        """Run 3-pass extraction on text with known entities."""
        if not entities or not text:
            return []

        relations: list[ExtractedRelation] = []

        # Pass 1: Entity-to-entity relationships
        p1 = await self._pass1_entity_relations(text, entities)
        relations.extend(p1)

        # Pass 2: Event extraction
        p2 = await self._pass2_events(text, entities)
        relations.extend(p2)

        # Pass 3: Temporal/spatial relationships
        p3 = await self._pass3_temporal_spatial(text, entities)
        relations.extend(p3)

        # Deduplicate
        relations = self._deduplicate(relations)

        logger.info(
            "relation_extraction.complete",
            total=len(relations),
            pass1=len(p1),
            pass2=len(p2),
            pass3=len(p3),
        )
        return relations

    async def _pass1_entity_relations(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        """Pass 1: Extract relationships between co-occurring entities."""
        if self._llm:
            return await self._llm_pass1(text, entities)
        return self._rule_pass1(text, entities)

    async def _pass2_events(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        """Pass 2: Extract events from text."""
        if self._llm:
            return await self._llm_pass2(text, entities)
        return self._rule_pass2(text, entities)

    async def _pass3_temporal_spatial(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        """Pass 3: Extract temporal/spatial relationships."""
        if self._llm:
            return await self._llm_pass3(text, entities)
        return self._rule_pass3(text, entities)

    # --- LLM-based passes ---

    async def _call_llm(self, prompt: str) -> list[dict]:
        """Call LLM and parse JSON response."""
        try:
            response = await self._llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000,
            )
            content = response.choices[0].message.content or "[]"
            # Extract JSON from response
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            logger.warning("relation_extraction.llm_failed", error=str(e))
            return []

    async def _llm_pass1(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        entity_strs = [f"{e.text} ({e.label})" for e in entities]
        prompt = PASS1_PROMPT.format(
            entities=", ".join(entity_strs),
            text=text[:3000],
            rel_types=", ".join(RELATIONSHIP_TYPES),
        )
        raw = await self._call_llm(prompt)
        results = []
        for r in raw:
            results.append(ExtractedRelation(
                source_entity=r.get("source", ""),
                target_entity=r.get("target", ""),
                relationship_type=r.get("type", "RELATED_TO"),
                confidence=min(float(r.get("confidence", 0.5)), 1.0),
                evidence_text=r.get("evidence", ""),
                extraction_method="llm",
            ))
        return results

    async def _llm_pass2(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        entity_strs = [f"{e.text} ({e.label})" for e in entities]
        prompt = PASS2_PROMPT.format(
            entities=", ".join(entity_strs),
            text=text[:3000],
            event_types=", ".join(EVENT_TYPES),
        )
        raw = await self._call_llm(prompt)
        results = []
        for r in raw:
            who = r.get("who", "")
            what = r.get("what", "")
            if who and what:
                results.append(ExtractedRelation(
                    source_entity=who,
                    target_entity=what,
                    relationship_type=f"EVENT_{r.get('type', 'UNKNOWN')}",
                    confidence=min(float(r.get("confidence", 0.5)), 1.0),
                    evidence_text=r.get("evidence", ""),
                    extraction_method="llm",
                    temporal_context=r.get("when"),
                    spatial_context=r.get("where"),
                ))
        return results

    async def _llm_pass3(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        entity_strs = [f"{e.text} ({e.label})" for e in entities]
        prompt = PASS3_PROMPT.format(
            entities=", ".join(entity_strs),
            text=text[:3000],
            types=", ".join(TEMPORAL_TYPES + SPATIAL_TYPES),
        )
        raw = await self._call_llm(prompt)
        results = []
        for r in raw:
            results.append(ExtractedRelation(
                source_entity=r.get("source", ""),
                target_entity=r.get("target", ""),
                relationship_type=r.get("type", "RELATED_TO"),
                confidence=min(float(r.get("confidence", 0.4)), 1.0),
                evidence_text=r.get("context", ""),
                extraction_method="llm",
            ))
        return results

    # --- Rule-based fallback passes ---

    def _rule_pass1(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        """Co-occurrence heuristic: entities in the same sentence are related."""
        sentences = re.split(r"[.!?\n]+", text)
        results: list[ExtractedRelation] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Find entities in this sentence
            in_sentence = [
                e for e in entities
                if e.text.lower() in sentence.lower()
            ]

            # Create pairwise MENTIONED relationships
            for i, e1 in enumerate(in_sentence):
                for e2 in in_sentence[i + 1:]:
                    if e1.label == e2.label and e1.text == e2.text:
                        continue

                    rel_type = self._infer_relationship_type(e1, e2)
                    results.append(ExtractedRelation(
                        source_entity=e1.text,
                        target_entity=e2.text,
                        relationship_type=rel_type,
                        confidence=0.4,
                        evidence_text=sentence[:200],
                        extraction_method="rule",
                    ))

        return results

    def _rule_pass2(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        """Simple event extraction using keyword patterns."""
        event_patterns = [
            (r"\b(attack(?:ed|ing)?|exploit(?:ed|ing)?|compromis(?:ed|ing))\b", "ATTACK"),
            (r"\b(travel(?:ed|ling)?|mov(?:ed|ing)|flew|sailed|drove)\b", "MOVEMENT"),
            (r"\b(contact(?:ed|ing)?|communicat(?:ed|ing)|messag(?:ed|ing)|call(?:ed|ing))\b", "COMMUNICATION"),
            (r"\b(register(?:ed|ing)?|creat(?:ed|ing)|sign(?:ed|ing) up)\b", "REGISTRATION"),
            (r"\b(spot(?:ted)|seen|observ(?:ed|ing)|detect(?:ed|ing))\b", "SIGHTING"),
        ]

        sentences = re.split(r"[.!?\n]+", text)
        results: list[ExtractedRelation] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            for pattern, event_type in event_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    in_sentence = [
                        e for e in entities if e.text.lower() in sentence.lower()
                    ]
                    if in_sentence:
                        results.append(ExtractedRelation(
                            source_entity=in_sentence[0].text,
                            target_entity=event_type,
                            relationship_type=f"EVENT_{event_type}",
                            confidence=0.35,
                            evidence_text=sentence[:200],
                            extraction_method="rule",
                        ))

        return results

    def _rule_pass3(
        self, text: str, entities: list[NEREntity]
    ) -> list[ExtractedRelation]:
        """Pattern-based temporal/spatial relationship extraction."""
        results: list[ExtractedRelation] = []

        # Location entities near other entities suggest LOCATED_AT
        location_entities = [e for e in entities if e.label == "Location"]
        non_location = [e for e in entities if e.label != "Location"]

        for loc in location_entities:
            for ent in non_location:
                # Check if they appear within 100 chars of each other
                distance = abs(loc.start - ent.start)
                if distance < 100:
                    results.append(ExtractedRelation(
                        source_entity=ent.text,
                        target_entity=loc.text,
                        relationship_type="LOCATED_AT",
                        confidence=0.3,
                        evidence_text="",
                        extraction_method="rule",
                        spatial_context=loc.text,
                    ))

        return results

    def _infer_relationship_type(self, e1: NEREntity, e2: NEREntity) -> str:
        """Infer relationship type from entity label pairs."""
        pair = frozenset([e1.label, e2.label])

        label_pair_map = {
            frozenset(["Person", "Organization"]): "AFFILIATED_WITH",
            frozenset(["Person", "Location"]): "LOCATED_AT",
            frozenset(["IPAddress", "Domain"]): "RESOLVES_TO",
            frozenset(["Domain", "IPAddress"]): "RESOLVES_TO",
            frozenset(["Person", "SocialAccount"]): "OWNS_ACCOUNT",
            frozenset(["Aircraft", "Location"]): "LOCATED_AT",
            frozenset(["Vessel", "Location"]): "LOCATED_AT",
            frozenset(["Organization", "Location"]): "LOCATED_AT",
        }

        return label_pair_map.get(pair, "RELATED_TO")

    def _deduplicate(
        self, relations: list[ExtractedRelation]
    ) -> list[ExtractedRelation]:
        """Deduplicate relations, keeping highest confidence."""
        seen: dict[str, ExtractedRelation] = {}

        for rel in relations:
            key = f"{rel.source_entity}:{rel.target_entity}:{rel.relationship_type}"
            reverse_key = f"{rel.target_entity}:{rel.source_entity}:{rel.relationship_type}"

            if key not in seen and reverse_key not in seen:
                seen[key] = rel
            else:
                existing_key = key if key in seen else reverse_key
                if rel.confidence > seen[existing_key].confidence:
                    seen[existing_key] = rel

        return list(seen.values())

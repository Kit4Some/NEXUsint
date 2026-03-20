"""Cross-source entity resolution — blocking, matching, merging."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from nexus.processing.ner import NEREntity

logger = structlog.get_logger()

# Entity labels with natural keys (exact match)
NATURAL_KEY_LABELS = {
    "IPAddress", "Domain", "Email", "Vessel", "Aircraft",
    "Vulnerability", "Hash", "CryptoWallet", "PhoneNumber",
}


@dataclass
class ResolvedEntity:
    """An entity after cross-source resolution."""

    canonical_name: str
    entity_type: str
    merged_properties: dict[str, Any] = field(default_factory=dict)
    source_entities: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    source_ints: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type,
            "merged_properties": self.merged_properties,
            "source_entities": self.source_entities,
            "confidence": self.confidence,
            "source_ints": list(self.source_ints),
        }


class EntityResolver:
    """Cross-source entity resolution pipeline."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        use_embeddings: bool = True,
    ) -> None:
        self._threshold = similarity_threshold
        self._use_embeddings = use_embeddings
        self._embedder = None

    def _load_embedder(self):
        """Lazy-load sentence transformer model."""
        if self._embedder is None and self._use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("entity_resolution.embedder_loaded")
            except Exception as e:
                logger.warning("entity_resolution.embedder_unavailable", error=str(e))
                self._use_embeddings = False
        return self._embedder

    def resolve(self, entities: list[NEREntity]) -> list[ResolvedEntity]:
        """Full entity resolution pipeline."""
        if not entities:
            return []

        # Group by label for efficient matching
        by_label: dict[str, list[NEREntity]] = {}
        for ent in entities:
            by_label.setdefault(ent.label, []).append(ent)

        resolved: list[ResolvedEntity] = []

        for label, group in by_label.items():
            if label in NATURAL_KEY_LABELS:
                # Step 2: Rule-based exact match on natural keys
                label_resolved = self._resolve_by_natural_key(group)
            else:
                # Step 1+3: TF-IDF blocking + embedding similarity
                label_resolved = self._resolve_by_similarity(group)

            resolved.extend(label_resolved)

        logger.info(
            "entity_resolution.complete",
            input_count=len(entities),
            resolved_count=len(resolved),
        )
        return resolved

    def _resolve_by_natural_key(
        self, entities: list[NEREntity]
    ) -> list[ResolvedEntity]:
        """Exact match on entity text for natural-key entities."""
        groups: dict[str, list[NEREntity]] = {}
        for ent in entities:
            key = ent.text.strip().lower()
            groups.setdefault(key, []).append(ent)

        results: list[ResolvedEntity] = []
        for key, group in groups.items():
            merged = self._merge_entity_group(group)
            results.append(merged)

        return results

    def _resolve_by_similarity(
        self, entities: list[NEREntity]
    ) -> list[ResolvedEntity]:
        """TF-IDF blocking + optional embedding similarity for fuzzy matching."""
        if len(entities) <= 1:
            return [self._merge_entity_group(entities)] if entities else []

        # Step 1: Build TF-IDF index for blocking
        try:
            candidate_pairs = self._tfidf_blocking(entities)
        except Exception:
            # Fallback: all pairs
            candidate_pairs = [
                (i, j) for i in range(len(entities)) for j in range(i + 1, len(entities))
            ]

        # Step 3: Embedding similarity (if available)
        if self._use_embeddings and candidate_pairs:
            match_pairs = self._embedding_matching(entities, candidate_pairs)
        else:
            # Fallback: exact text match only
            match_pairs = [
                (i, j) for i, j in candidate_pairs
                if entities[i].text.lower() == entities[j].text.lower()
            ]

        # Build connected components from matched pairs
        components = self._connected_components(len(entities), match_pairs)

        results: list[ResolvedEntity] = []
        for component in components:
            group = [entities[i] for i in component]
            results.append(self._merge_entity_group(group))

        return results

    def _tfidf_blocking(
        self, entities: list[NEREntity], threshold: float = 0.3
    ) -> list[tuple[int, int]]:
        """Generate candidate pairs using TF-IDF cosine similarity."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        texts = [e.text for e in entities]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        tfidf_matrix = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf_matrix)

        pairs: list[tuple[int, int]] = []
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                if sim_matrix[i, j] >= threshold:
                    pairs.append((i, j))

        return pairs

    def _embedding_matching(
        self, entities: list[NEREntity], candidates: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """Filter candidate pairs by embedding cosine similarity."""
        embedder = self._load_embedder()
        if not embedder:
            return [
                (i, j) for i, j in candidates
                if entities[i].text.lower() == entities[j].text.lower()
            ]

        # Compute embeddings for unique entity texts
        unique_indices = sorted(set(i for pair in candidates for i in pair))
        texts = [entities[i].text for i in unique_indices]
        embeddings = embedder.encode(texts, show_progress_bar=False)

        idx_to_emb = {idx: emb for idx, emb in zip(unique_indices, embeddings)}

        import numpy as np

        matches: list[tuple[int, int]] = []
        for i, j in candidates:
            if i in idx_to_emb and j in idx_to_emb:
                sim = float(np.dot(idx_to_emb[i], idx_to_emb[j]) / (
                    np.linalg.norm(idx_to_emb[i]) * np.linalg.norm(idx_to_emb[j]) + 1e-10
                ))
                if sim >= self._threshold:
                    matches.append((i, j))

        return matches

    def _connected_components(
        self, n: int, edges: list[tuple[int, int]]
    ) -> list[list[int]]:
        """Find connected components using union-find."""
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i, j in edges:
            union(i, j)

        groups: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(i)

        return list(groups.values())

    def _merge_entity_group(
        self, entities: list[NEREntity]
    ) -> ResolvedEntity:
        """Merge a group of matched entities into a single resolved entity."""
        # Use the entity with highest confidence as canonical
        best = max(entities, key=lambda e: e.confidence)

        source_ints = set()
        source_entities = []
        for ent in entities:
            source_entities.append(ent.to_dict())
            if ent.source:
                # Extract INT type from source if available
                for int_type in ("CYBINT", "SOCMINT", "SIGINT", "GEOINT"):
                    if int_type.lower() in ent.source.lower():
                        source_ints.add(int_type)

        # Combined confidence: average boosted by source count
        avg_conf = sum(e.confidence for e in entities) / len(entities)
        source_boost = min(len(entities) * 0.05, 0.2)
        combined_confidence = min(avg_conf + source_boost, 1.0)

        return ResolvedEntity(
            canonical_name=best.text,
            entity_type=best.label,
            merged_properties={
                "all_names": list(set(e.text for e in entities)),
                "first_seen_offset": min(e.start for e in entities),
                "mention_count": len(entities),
            },
            source_entities=source_entities,
            confidence=combined_confidence,
            source_ints=source_ints,
        )

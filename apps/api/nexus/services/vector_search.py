"""pgvector semantic search service using OpenAI embeddings."""

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


class VectorSearchService:
    def __init__(self, pg_pool, openai_api_key: str):
        self._pool = pg_pool
        self._openai = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector using OpenAI API."""
        if not self._openai:
            raise RuntimeError("OpenAI API key not configured for vector search")
        response = await self._openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:8000],
        )
        return response.data[0].embedding

    async def upsert_entity_embedding(
        self,
        entity_id: str,
        entity_type: str,
        entity_name: str,
        source_int: str,
        embedding: list[float],
    ):
        """Insert or update embedding in entity_embeddings table."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO entity_embeddings (entity_id, type, name, embedding, source_int)
                VALUES ($1, $2, $3, $4::vector, $5)
                ON CONFLICT (entity_id) DO UPDATE SET
                    type = EXCLUDED.type,
                    name = EXCLUDED.name,
                    embedding = EXCLUDED.embedding,
                    source_int = EXCLUDED.source_int
                """,
                entity_id,
                entity_type,
                entity_name,
                str(embedding),
                source_int,
            )

    async def search_similar(
        self, query: str, top_k: int = 20, threshold: float = 0.7
    ) -> list[dict]:
        """Semantic similarity search via pgvector cosine distance."""
        query_embedding = await self.generate_embedding(query)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT entity_id, type, name, source_int,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM entity_embeddings
                WHERE 1 - (embedding <=> $1::vector) >= $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                str(query_embedding),
                threshold,
                top_k,
            )

        return [
            {
                "entity_id": row["entity_id"],
                "entity_type": row["type"],
                "entity_name": row["name"],
                "source_int": row["source_int"],
                "similarity": float(row["similarity"]),
            }
            for row in rows
        ]

    async def bulk_embed_entities(self, entities: list[dict]):
        """Generate and store embeddings for multiple entities."""
        if not self._openai or not entities:
            return

        texts = [f"{e.get('type', '')} {e.get('name', '')} {e.get('description', '')}" for e in entities]

        # Batch in groups of 2048
        for i in range(0, len(texts), 2048):
            batch = texts[i : i + 2048]
            batch_entities = entities[i : i + 2048]

            response = await self._openai.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )

            async with self._pool.acquire() as conn:
                for j, emb_data in enumerate(response.data):
                    entity = batch_entities[j]
                    await conn.execute(
                        """
                        INSERT INTO entity_embeddings (entity_id, type, name, embedding, source_int)
                        VALUES ($1, $2, $3, $4::vector, $5)
                        ON CONFLICT (entity_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding
                        """,
                        entity.get("id", ""),
                        entity.get("type", ""),
                        entity.get("name", ""),
                        str(emb_data.embedding),
                        entity.get("sourceInt", entity.get("source_int", "")),
                    )

        logger.info("vector_search.bulk_embed_complete", count=len(entities))

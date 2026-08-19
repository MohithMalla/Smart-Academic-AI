from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.services.ai.base import BaseEmbeddingProvider


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    page_number: Optional[int]
    text: str
    rrf_score: float
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None


class HybridRetriever:
    """Hybrid Retriever combining pgvector Cosine Search + PostgreSQL Full-Text Search via Reciprocal Rank Fusion (RRF)."""

    def __init__(self, embedder: BaseEmbeddingProvider):
        self.embedder = embedder

    async def search(
        self,
        db: AsyncSession,
        query: str,
        tenant_id: UUID,
        course_id: UUID,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedChunk]:
        dialect_name = db.bind.dialect.name if db.bind else "postgresql"

        # SQLite fallback path for unit/integration tests
        if dialect_name == "sqlite":
            return await self._sqlite_search(db, query, tenant_id, course_id, top_k, filters)

        # 1. Generate query embedding for PostgreSQL pgvector
        query_embedding = await self.embedder.embed_text(query)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Build dynamic SQL filter clauses for subject, chapter, topic, document_id
        filter_sql = ""
        params: Dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "course_id": str(course_id),
            "query_embedding": embedding_str,
            "query_text": query,
            "top_k": top_k
        }

        if filters:
            if filters.get("subject"):
                filter_sql += " AND subject = :filter_subject"
                params["filter_subject"] = filters["subject"]
            if filters.get("chapter"):
                filter_sql += " AND chapter = :filter_chapter"
                params["filter_chapter"] = filters["chapter"]
            if filters.get("topic"):
                filter_sql += " AND topic = :filter_topic"
                params["filter_topic"] = filters["topic"]
            if filters.get("document_id"):
                filter_sql += " AND document_id = :filter_doc_id"
                params["filter_doc_id"] = str(filters["document_id"])

        # Reciprocal Rank Fusion SQL query over tenant-isolated chunks in PostgreSQL
        rrf_sql = text(f"""
            WITH vector_matches AS (
                SELECT id, document_id, page_number, text, subject, chapter, topic,
                       ROW_NUMBER() OVER (ORDER BY embedding <=> :query_embedding) AS rank
                FROM document_chunks
                WHERE institution_id = :tenant_id 
                  AND course_id = :course_id
                  {filter_sql}
                LIMIT 20
            ),
            text_matches AS (
                SELECT id, document_id, page_number, text, subject, chapter, topic,
                       ROW_NUMBER() OVER (ORDER BY ts_rank_cd(to_tsvector('english', text), plainto_tsquery('english', :query_text)) DESC) AS rank
                FROM document_chunks
                WHERE institution_id = :tenant_id 
                  AND course_id = :course_id
                  AND to_tsvector('english', text) @@ plainto_tsquery('english', :query_text)
                  {filter_sql}
                LIMIT 20
            )
            SELECT 
                COALESCE(v.id, t.id) AS chunk_id,
                COALESCE(v.document_id, t.document_id) AS document_id,
                COALESCE(v.page_number, t.page_number) AS page_number,
                COALESCE(v.text, t.text) AS text,
                COALESCE(v.subject, t.subject) AS subject,
                COALESCE(v.chapter, t.chapter) AS chapter,
                COALESCE(v.topic, t.topic) AS topic,
                (COALESCE(1.0 / (60 + v.rank), 0.0) + COALESCE(1.0 / (60 + t.rank), 0.0)) AS rrf_score
            FROM vector_matches v
            FULL OUTER JOIN text_matches t ON v.id = t.id
            ORDER BY rrf_score DESC
            LIMIT :top_k;
        """)

        res = await db.execute(rrf_sql, params)
        rows = res.mappings().all()

        retrieved: List[RetrievedChunk] = []
        for row in rows:
            retrieved.append(
                RetrievedChunk(
                    chunk_id=UUID(str(row["chunk_id"])),
                    document_id=UUID(str(row["document_id"])),
                    page_number=row["page_number"],
                    text=row["text"],
                    rrf_score=float(row["rrf_score"]),
                    subject=row["subject"],
                    chapter=row["chapter"],
                    topic=row["topic"]
                )
            )

        return retrieved

    async def _sqlite_search(
        self,
        db: AsyncSession,
        query: str,
        tenant_id: UUID,
        course_id: UUID,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedChunk]:
        stmt = select(DocumentChunk).where(
            DocumentChunk.institution_id == tenant_id,
            DocumentChunk.course_id == course_id
        )

        if filters:
            if filters.get("subject"):
                stmt = stmt.where(DocumentChunk.subject == filters["subject"])
            if filters.get("chapter"):
                stmt = stmt.where(DocumentChunk.chapter == filters["chapter"])
            if filters.get("topic"):
                stmt = stmt.where(DocumentChunk.topic == filters["topic"])
            if filters.get("document_id"):
                stmt = stmt.where(DocumentChunk.document_id == filters["document_id"])

        res = await db.execute(stmt)
        chunks = res.scalars().all()

        # Score chunks in Python for SQLite test driver
        scored: List[tuple[DocumentChunk, float]] = []
        q_words = set(query.lower().split())

        for idx, c in enumerate(chunks):
            c_words = set(c.text.lower().split())
            common = q_words.intersection(c_words)
            score = len(common) / max(1, len(q_words)) + 1.0 / (60 + idx + 1)
            scored.append((c, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_chunks = scored[:top_k]

        return [
            RetrievedChunk(
                chunk_id=c.id,
                document_id=c.document_id,
                page_number=c.page_number,
                text=c.text,
                rrf_score=round(s, 4),
                subject=c.subject,
                chapter=c.chapter,
                topic=c.topic
            )
            for c, s in top_chunks
        ]

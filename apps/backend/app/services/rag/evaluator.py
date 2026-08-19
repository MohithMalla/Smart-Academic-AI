import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.generator import RAGGenerator
from app.services.rag.retriever import HybridRetriever


@dataclass
class EvaluationMetrics:
    total_evaluations: int
    retrieval_hits: int
    retrieval_hit_rate: float
    citation_hits: int
    citation_hit_rate: float


class RAGEvaluator:
    """RAG Quality Benchmarking Suite evaluating retrieval hit rate and citation accuracy."""

    def __init__(self, retriever: HybridRetriever, generator: RAGGenerator):
        self.retriever = retriever
        self.generator = generator

    async def evaluate_dataset(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        course_id: UUID,
        dataset_path: Path
    ) -> EvaluationMetrics:
        with open(dataset_path, "r") as f:
            dataset = json.load(f)

        total = len(dataset)
        retrieval_hits = 0
        citation_hits = 0

        for item in dataset:
            query = item["question"]
            expected_doc = item.get("expected_document")

            # 1. Retrieve chunks
            chunks = await self.retriever.search(
                db=db,
                query=query,
                tenant_id=tenant_id,
                course_id=course_id,
                top_k=5
            )

            # Check if expected document is in retrieved chunks
            doc_titles = await self.generator._resolve_document_titles(db, tenant_id, chunks)
            retrieved_doc_names = [doc_titles.get(c.document_id, "") for c in chunks]

            hit = any(expected_doc.lower() in name.lower() for name in retrieved_doc_names) if expected_doc else False
            if hit or not expected_doc:
                retrieval_hits += 1

            # 2. Generate RAG answer
            rag_output = await self.generator.generate_answer(
                db=db,
                tenant_id=tenant_id,
                user_id=tenant_id,
                query=query,
                chunks=chunks
            )

            citations = rag_output.get("citations", [])
            cited_names = [c["document_name"] for c in citations]

            cite_hit = any(expected_doc.lower() in name.lower() for name in cited_names) if expected_doc else False
            if cite_hit or not expected_doc:
                citation_hits += 1

        retrieval_rate = (retrieval_hits / total) if total > 0 else 0.0
        citation_rate = (citation_hits / total) if total > 0 else 0.0

        return EvaluationMetrics(
            total_evaluations=total,
            retrieval_hits=retrieval_hits,
            retrieval_hit_rate=round(retrieval_rate, 4),
            citation_hits=citation_hits,
            citation_hit_rate=round(citation_rate, 4)
        )

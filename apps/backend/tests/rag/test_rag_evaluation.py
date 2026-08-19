from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.mock import MockEmbeddingProvider, MockLLMProvider
from app.services.rag.evaluator import RAGEvaluator
from app.services.rag.generator import RAGGenerator
from app.services.rag.retriever import HybridRetriever

DATASET_PATH = Path(__file__).parent / "evaluation_dataset.json"


@pytest.mark.asyncio
async def test_rag_evaluator_metrics(db_session: AsyncSession, setup_test_tenants: dict):
    inst_a_id = setup_test_tenants["inst_a"].id

    embedder = MockEmbeddingProvider()
    llm = MockLLMProvider()
    retriever = HybridRetriever(embedder)
    generator = RAGGenerator(llm)
    evaluator = RAGEvaluator(retriever, generator)

    metrics = await evaluator.evaluate_dataset(
        db=db_session,
        tenant_id=inst_a_id,
        course_id=inst_a_id,
        dataset_path=DATASET_PATH
    )

    assert metrics.total_evaluations == 20
    assert metrics.retrieval_hit_rate >= 0.0
    assert metrics.citation_hit_rate >= 0.0

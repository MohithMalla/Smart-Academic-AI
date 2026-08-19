import os
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_tenant_context
from app.dependencies.tenant import TenantContext
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.rag import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    RAGQueryRequest,
    RAGQueryResponse
)
from app.services.ai.gemini import GeminiEmbeddingProvider, GeminiLLMProvider
from app.services.ai.mock import MockEmbeddingProvider, MockLLMProvider
from app.services.rag.generator import RAGGenerator
from app.services.rag.retriever import HybridRetriever

router = APIRouter(prefix="/rag", tags=["RAG & Academic Intelligence"])


def get_ai_providers():
    """Factory returning production Gemini or Mock providers based on GEMINI_API_KEY presence."""
    if os.getenv("GEMINI_API_KEY"):
        return GeminiEmbeddingProvider(), GeminiLLMProvider()
    return MockEmbeddingProvider(), MockLLMProvider()


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    req: RAGQueryRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Execute grounded academic RAG query with hybrid retrieval and source citations."""
    embedder, llm = get_ai_providers()
    retriever = HybridRetriever(embedder)
    generator = RAGGenerator(llm)

    filter_dict = req.filters.model_dump(exclude_unset=True) if req.filters else {}

    chunks = await retriever.search(
        db=db,
        query=req.query,
        tenant_id=tenant_ctx.institution_id,
        course_id=req.course_id,
        top_k=req.top_k,
        filters=filter_dict
    )

    result = await generator.generate_answer(
        db=db,
        tenant_id=tenant_ctx.institution_id,
        user_id=tenant_ctx.user_id,
        query=req.query,
        chunks=chunks
    )

    return result


@router.post("/stream")
async def stream_rag_query(
    req: RAGQueryRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Server-Sent Events (SSE) streaming endpoint for RAG generation."""
    embedder, llm = get_ai_providers()
    retriever = HybridRetriever(embedder)
    generator = RAGGenerator(llm)

    filter_dict = req.filters.model_dump(exclude_unset=True) if req.filters else {}

    chunks = await retriever.search(
        db=db,
        query=req.query,
        tenant_id=tenant_ctx.institution_id,
        course_id=req.course_id,
        top_k=req.top_k,
        filters=filter_dict
    )

    return StreamingResponse(
        generator.stream_answer(
            db=db,
            tenant_id=tenant_ctx.institution_id,
            user_id=tenant_ctx.user_id,
            query=req.query,
            chunks=chunks
        ),
        media_type="text/event-stream"
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: ConversationCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant-scoped RAG conversation thread."""
    conv = Conversation(
        institution_id=tenant_ctx.institution_id,
        user_id=tenant_ctx.user_id,
        course_id=req.course_id,
        title=req.title
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """List conversation threads belonging strictly to current user and tenant."""
    stmt = select(Conversation).where(
        Conversation.institution_id == tenant_ctx.institution_id,
        Conversation.user_id == tenant_ctx.user_id
    ).order_by(Conversation.created_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """List messages within a conversation enforcing tenant isolation."""
    stmt_conv = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.institution_id == tenant_ctx.institution_id,
        Conversation.user_id == tenant_ctx.user_id
    )
    conv_res = await db.execute(stmt_conv)
    if not conv_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation thread not found or access forbidden."
        )

    stmt_msgs = select(Message).where(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc())
    res = await db.execute(stmt_msgs)
    return list(res.scalars().all())

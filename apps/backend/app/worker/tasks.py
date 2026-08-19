import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.ai.gemini import GeminiEmbeddingProvider
from app.services.ai.mock import MockEmbeddingProvider
from app.services.chunker import Chunker
from app.services.extractors.docx import DOCXExtractor
from app.services.extractors.pdf import PDFExtractor
from app.services.extractors.txt import TXTExtractor
from app.services.storage.local import LocalStorageProvider


def get_extractor(mime_type: str, filename: str):
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if "pdf" in mime_type or ext == "pdf":
        return PDFExtractor()
    elif "docx" in mime_type or "word" in mime_type or ext == "docx":
        return DOCXExtractor()
    elif "text" in mime_type or ext == "txt":
        return TXTExtractor()
    else:
        raise ValueError(f"Unsupported document format: {mime_type} ({filename})")


async def _async_process_document(
    document_id_str: str,
    use_mock_ai: bool = False,
    db_session: Optional[AsyncSession] = None
):
    document_id = UUID(document_id_str)
    storage = LocalStorageProvider()
    chunker = Chunker(chunk_size=1500, chunk_overlap=200)
    embedder = MockEmbeddingProvider() if use_mock_ai else GeminiEmbeddingProvider()

    if db_session:
        return await _execute_processing_pipeline(db_session, document_id, storage, chunker, embedder)
    else:
        async with AsyncSessionLocal() as db:
            return await _execute_processing_pipeline(db, document_id, storage, chunker, embedder)


async def _execute_processing_pipeline(db: AsyncSession, document_id: UUID, storage, chunker, embedder):
    stmt = select(Document).where(Document.id == document_id)
    res = await db.execute(stmt)
    doc_record = res.scalar_one_or_none()

    if not doc_record:
        return {"status": "FAILED", "reason": "Document not found"}

    try:
        # 1. Update status to PROCESSING
        doc_record.status = DocumentStatus.PROCESSING
        doc_record.error_message = None
        await db.commit()

        # 2. Read file bytes from storage
        file_bytes = await storage.get_file(doc_record.storage_path)

        # 3. Extract Text Pages
        extractor = get_extractor(doc_record.mime_type, doc_record.original_filename)
        extracted = extractor.extract(file_bytes)
        
        doc_record.page_count = extracted.page_count

        # 4. Chunk Document
        chunks_data = chunker.chunk_document(extracted)
        if not chunks_data:
            raise ValueError("Document contains no extractable chunks")

        # 5. Generate Batch Embeddings
        chunk_texts = [c.text for c in chunks_data]
        embeddings = await embedder.embed_batch(chunk_texts)

        # 6. Persist DocumentChunks
        db_chunks = []
        for c_data, emb in zip(chunks_data, embeddings):
            db_chunk = DocumentChunk(
                institution_id=doc_record.institution_id,
                course_id=doc_record.course_id,
                document_id=doc_record.id,
                chunk_index=c_data.chunk_index,
                page_number=c_data.page_number,
                text=c_data.text,
                subject=c_data.subject,
                chapter=c_data.chapter,
                topic=c_data.topic,
                embedding=emb,
                metadata_json={"token_count": c_data.token_count}
            )
            db_chunks.append(db_chunk)

        db.add_all(db_chunks)

        # 7. Mark COMPLETED
        doc_record.status = DocumentStatus.COMPLETED
        doc_record.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return {"status": "COMPLETED", "chunks": len(db_chunks)}
    except Exception as e:
        await db.rollback()
        res_fail = await db.execute(select(Document).where(Document.id == document_id))
        fail_doc = res_fail.scalar_one_or_none()
        if fail_doc:
            fail_doc.status = DocumentStatus.FAILED
            fail_doc.error_message = f"Processing failed: {str(e)}"
            await db.commit()
        return {"status": "FAILED", "error": str(e)}


async def _async_delete_document_data(document_id_str: str, db_session: Optional[AsyncSession] = None):
    document_id = UUID(document_id_str)
    storage = LocalStorageProvider()

    if db_session:
        return await _execute_deletion_pipeline(db_session, document_id, storage)
    else:
        async with AsyncSessionLocal() as db:
            return await _execute_deletion_pipeline(db, document_id, storage)


async def _execute_deletion_pipeline(db: AsyncSession, document_id: UUID, storage):
    stmt = select(Document).where(Document.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if doc:
        await storage.delete_file(doc.storage_path)
        await db.delete(doc)
        await db.commit()
        return {"status": "DELETED"}
    return {"status": "NOT_FOUND"}


@shared_task(name="process_document")
def process_document(document_id_str: str, use_mock_ai: bool = False):
    return asyncio.run(_async_process_document(document_id_str, use_mock_ai))


@shared_task(name="generate_embeddings")
def generate_embeddings(document_id_str: str, use_mock_ai: bool = False):
    return asyncio.run(_async_process_document(document_id_str, use_mock_ai))


@shared_task(name="delete_document_data")
def delete_document_data(document_id_str: str):
    return asyncio.run(_async_delete_document_data(document_id_str))

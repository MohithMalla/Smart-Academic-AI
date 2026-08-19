from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_tenant_context, require_roles
from app.dependencies.tenant import TenantContext
from app.models.course import Course
from app.models.document import Document, DocumentStatus
from app.models.user import Role
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services.storage.local import LocalStorageProvider
from app.worker.tasks import delete_document_data, process_document

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB max limit


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(Role.INSTITUTION_ADMIN, Role.TEACHER))]
)
async def upload_document(
    course_id: UUID = Form(...),
    file: UploadFile = File(...),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Upload academic document (PDF/DOCX/TXT) and dispatch background processing."""
    # 1. Validate file extension
    original_filename = file.filename or "uploaded_doc.pdf"
    ext = "." + original_filename.split(".")[-1].lower() if "." in original_filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {list(ALLOWED_EXTENSIONS)}"
        )

    # 2. Read bytes & check size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is empty."
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of 50MB."
        )

    # 3. Verify course belongs to tenant
    course_stmt = select(Course).where(
        Course.id == course_id,
        Course.institution_id == tenant_ctx.institution_id
    )
    course_res = await db.execute(course_stmt)
    if not course_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or access forbidden."
        )

    # 4. Save file to storage provider
    storage = LocalStorageProvider()
    rel_storage_path = await storage.save_file(
        file_bytes=file_bytes,
        institution_id=tenant_ctx.institution_id,
        course_id=course_id,
        original_filename=original_filename
    )

    # 5. Create Document record in DB
    doc_record = Document(
        institution_id=tenant_ctx.institution_id,
        course_id=course_id,
        uploaded_by=tenant_ctx.user_id,
        filename=rel_storage_path.split("/")[-1],
        original_filename=original_filename,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        storage_path=rel_storage_path,
        status=DocumentStatus.PROCESSING
    )
    db.add(doc_record)
    await db.commit()
    await db.refresh(doc_record)

    # 6. Dispatch processing (Celery delay in production, inline fallback using active db session)
    try:
        process_document.delay(str(doc_record.id))
    except Exception:
        from app.worker.tasks import _async_process_document
        await _async_process_document(str(doc_record.id), use_mock_ai=True, db_session=db)

    return DocumentUploadResponse(
        document_id=doc_record.id,
        filename=original_filename,
        status=DocumentStatus.PROCESSING,
        message="Document uploaded and queued for processing."
    )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    course_id: Optional[UUID] = Query(None),
    status_filter: Optional[DocumentStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """List documents for tenant with optional course and status filtering."""
    stmt = select(Document).where(Document.institution_id == tenant_ctx.institution_id)

    if course_id:
        stmt = stmt.where(Document.course_id == course_id)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)

    offset = (page - 1) * limit
    stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Fetch single document details enforcing strict tenant isolation."""
    stmt = select(Document).where(
        Document.id == document_id,
        Document.institution_id == tenant_ctx.institution_id
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access forbidden."
        )
    return doc


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Check processing status of a document."""
    doc = await get_document(document_id, tenant_ctx, db)
    return {
        "document_id": doc.id,
        "status": doc.status,
        "page_count": doc.page_count,
        "error_message": doc.error_message,
        "completed_at": doc.completed_at
    }


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Delete document, storage asset, and vector chunks enforcing tenant boundary."""
    doc = await get_document(document_id, tenant_ctx, db)

    try:
        delete_document_data.delay(str(doc.id))
    except Exception:
        from app.worker.tasks import _async_delete_document_data
        await _async_delete_document_data(str(doc.id), db_session=db)

    return {"message": "Document deletion initiated successfully."}
